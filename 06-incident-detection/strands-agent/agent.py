"""
Incident Remediation Agent — Strands Agents implementation.

Tools ported from lambda/idr-bedrock-agent-action-group-good.py.
Mutating tools (scale_up_instance, increase_iops, increase_storage_size,
increase_acu) require confirm=True so the agent must ask the operator
before executing any write action.

run_query is hard-wired read-only: it rejects non-SELECT-family statements
AND opens the connection with read_only=True (psycopg v3).
"""

from __future__ import annotations

import json
import logging
import os
import re
import traceback
from datetime import datetime, timedelta
from typing import Optional

import boto3
import psycopg
from botocore.client import Config
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# AWS clients (module-level; reused across tool calls)
# ---------------------------------------------------------------------------

_region = os.environ.get("AWS_REGION", "us-west-2")
_cfg = Config(connect_timeout=5, retries={"max_attempts": 0})

rds_client = boto3.client("rds", region_name=_region, config=_cfg)
secrets_client = boto3.client("secretsmanager", region_name=_region, config=_cfg)
cw_client = boto3.client("cloudwatch", region_name=_region, config=_cfg)

# ---------------------------------------------------------------------------
# Instance-class ordering used by scale_up_instance
# ---------------------------------------------------------------------------
_CLASS_ORDER = [
    "micro", "small", "medium", "large", "xlarge",
    "2xlarge", "4xlarge", "8xlarge", "12xlarge", "14xlarge",
    "16xlarge", "32xlarge", "na",
]

# ---------------------------------------------------------------------------
# Private helpers (not exposed as tools)
# ---------------------------------------------------------------------------

def _get_db_secret_name() -> str:
    """Return the Secrets Manager secret name from env, with fallback pattern."""
    return os.environ.get("DB_SECRET_NAME", "{db_instance_identifier}-agent-secret")


def _get_connection(db_instance_identifier: str) -> psycopg.Connection:
    """Open a psycopg v3 read-only connection using the stored secret."""
    secret_name = _get_db_secret_name()
    if "{db_instance_identifier}" in secret_name:
        secret_name = secret_name.replace("{db_instance_identifier}", db_instance_identifier)

    resp = secrets_client.get_secret_value(SecretId=secret_name)
    creds = json.loads(resp["SecretString"])
    conn = psycopg.connect(
        host=creds["host"],
        port=int(creds.get("port", 5432)),
        user=creds["username"],
        password=creds["password"],
        # Enforce read-only at the connection level
        options="-c default_transaction_read_only=on",
    )
    conn.read_only = True
    return conn


def _describe_instance(db_instance_identifier: str) -> dict:
    """Return the first DBInstance dict from describe_db_instances."""
    resp = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    return resp["DBInstances"][0]


def _describe_cluster(cluster_id: str) -> dict:
    resp = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
    return resp["DBClusters"][0]


def _get_cluster_name(db_instance_identifier: str) -> str:
    instance = _describe_instance(db_instance_identifier)
    return instance["DBClusterIdentifier"]


def _get_max_acu_value(db_instance_identifier: str) -> float:
    cluster_id = _get_cluster_name(db_instance_identifier)
    cluster = _describe_cluster(cluster_id)
    return cluster["ServerlessV2ScalingConfiguration"]["MaxCapacity"]


def _next_instance_class(db_instance_identifier: str, current_class: str) -> str:
    """Return the next-larger DB instance class, or 'NA' if at the top."""
    parts = current_class.split(".")  # e.g. ["db", "r6g", "2xlarge"]
    if len(parts) < 3:
        return "NA"
    size = parts[2]
    next_size = None
    for idx, cls in enumerate(_CLASS_ORDER):
        if cls == size:
            # Guard against IndexError at the end of the list
            if idx + 1 < len(_CLASS_ORDER):
                next_size = _CLASS_ORDER[idx + 1]
            break

    if next_size is None or next_size == "na":
        return "NA"

    next_class = f"{parts[0]}.{parts[1]}.{next_size}"
    logger.info("Checking availability of %s", next_class)

    instance = _describe_instance(db_instance_identifier)
    resp = rds_client.describe_orderable_db_instance_options(
        Engine=instance["Engine"],
        EngineVersion=instance["EngineVersion"],
        Vpc=True,
        DBInstanceClass=next_class,
    )
    if len(resp.get("OrderableDBInstanceOptions", [])) > 0:
        return next_class
    raise RuntimeError(f"Next class {next_class} is not orderable in this VPC/region")


def _cw_metric_max(
    db_instance_identifier: str,
    metric_name: str,
    metric_time_hours: int,
) -> Optional[float]:
    """Fetch a single-metric Maximum over the given time window. Returns None if no data."""
    now = datetime.utcnow()
    start = now - timedelta(hours=metric_time_hours)
    period = metric_time_hours * 3600
    resp = cw_client.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "q1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/RDS",
                        "MetricName": metric_name,
                        "Dimensions": [
                            {"Name": "DBInstanceIdentifier", "Value": db_instance_identifier}
                        ],
                    },
                    "Period": period,
                    "Stat": "Maximum",
                },
            }
        ],
        StartTime=start,
        EndTime=now,
    )
    values = resp["MetricDataResults"][0].get("Values", [])
    # Guard against empty response (IndexError from original code)
    if not values:
        return None
    return values[0]


# ---------------------------------------------------------------------------
# @tool functions — these become the agent's capabilities
# ---------------------------------------------------------------------------


@tool
def get_instance_details(db_instance_identifier: str) -> str:
    """Retrieve full RDS instance details as JSON.

    Args:
        db_instance_identifier: The RDS DB instance identifier.

    Returns:
        JSON string with all instance attributes (class, engine, status, storage, etc.).
    """
    try:
        details = _describe_instance(db_instance_identifier)
        return json.dumps(details, indent=2, sort_keys=True, default=str)
    except Exception as exc:
        logger.error("get_instance_details failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def get_cpu_metrics(db_instance_identifier: str, metric_time_hours: int) -> str:
    """Retrieve the maximum CPU utilization over a time window from CloudWatch.

    Args:
        db_instance_identifier: The RDS DB instance identifier.
        metric_time_hours: Number of hours to look back (e.g. 1, 6, 24).

    Returns:
        A string describing maximum CPU utilization percentage.
    """
    try:
        value = _cw_metric_max(db_instance_identifier, "CPUUtilization", metric_time_hours)
        if value is None:
            return "No CPUUtilization datapoints available for the requested window."
        return f"Maximum CPU utilization over the last {metric_time_hours}h is {int(value)}%"
    except Exception as exc:
        logger.error("get_cpu_metrics failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def get_iops_metrics(db_instance_identifier: str, metric_time_hours: int) -> str:
    """Retrieve maximum total IOPS (ReadIOPS + WriteIOPS) from CloudWatch.

    Args:
        db_instance_identifier: The RDS DB instance identifier.
        metric_time_hours: Number of hours to look back.

    Returns:
        A string describing maximum combined IOPS.
    """
    try:
        now = datetime.utcnow()
        start = now - timedelta(hours=metric_time_hours)
        period = metric_time_hours * 3600
        resp = cw_client.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "total",
                    "Expression": "read_iops + write_iops",
                    "Label": "TotalIOPS",
                },
                {
                    "Id": "read_iops",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "ReadIOPS",
                            "Dimensions": [
                                {"Name": "DBInstanceIdentifier", "Value": db_instance_identifier}
                            ],
                        },
                        "Period": period,
                        "Stat": "Maximum",
                    },
                    "ReturnData": False,
                },
                {
                    "Id": "write_iops",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/RDS",
                            "MetricName": "WriteIOPS",
                            "Dimensions": [
                                {"Name": "DBInstanceIdentifier", "Value": db_instance_identifier}
                            ],
                        },
                        "Period": period,
                        "Stat": "Maximum",
                    },
                    "ReturnData": False,
                },
            ],
            StartTime=start,
            EndTime=now,
        )
        values = resp["MetricDataResults"][0].get("Values", [])
        # Guard against empty response
        if not values:
            return "No IOPS datapoints available for the requested window."
        return f"Maximum total IOPS over the last {metric_time_hours}h is {int(values[0])}"
    except Exception as exc:
        logger.error("get_iops_metrics failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def get_max_acu(db_instance_identifier: str) -> str:
    """Retrieve the current max ACU (Aurora Capacity Units) limit for the serverless cluster.

    Args:
        db_instance_identifier: The RDS DB instance identifier in the serverless cluster.

    Returns:
        A string stating the current max ACU configuration.
    """
    try:
        max_acu = _get_max_acu_value(db_instance_identifier)
        return f"Current max ACU for instance {db_instance_identifier} is {max_acu}"
    except Exception as exc:
        logger.error("get_max_acu failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def run_query(db_instance_identifier: str, query: str) -> str:
    """Execute a read-only SQL query against the RDS instance and return results.

    Only SELECT, SHOW, EXPLAIN, and WITH (CTE) statements pass the first-keyword
    check. Note the keyword check alone is not a security boundary (a CTE can
    embed a write, e.g. WITH x AS (DELETE ...) SELECT 1) — the actual enforcement
    is the database connection itself, which is opened with read_only=True and
    default_transaction_read_only=on, so any write is rejected server-side.

    Args:
        db_instance_identifier: The RDS DB instance identifier.
        query: A read-only SQL query (SELECT / SHOW / EXPLAIN / WITH only).

    Returns:
        JSON-formatted query results, or an error message.
    """
    try:
        # Strip leading SQL comments and whitespace, then check first keyword
        cleaned = re.sub(r"(/\*.*?\*/|--[^\n]*)", "", query, flags=re.DOTALL).strip()
        first_keyword = cleaned.split()[0].upper() if cleaned.split() else ""
        allowed_keywords = {"SELECT", "SHOW", "EXPLAIN", "WITH"}
        if first_keyword not in allowed_keywords:
            return (
                f"REJECTED: only read-only statements (SELECT/SHOW/EXPLAIN/WITH) are permitted. "
                f"Got: '{first_keyword}'"
            )

        conn = _get_connection(db_instance_identifier)
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                col_names = [desc.name for desc in cur.description] if cur.description else []
                results = [dict(zip(col_names, row)) for row in rows]
                return json.dumps(results, default=str, indent=2)
        finally:
            conn.close()
    except Exception as exc:
        logger.error("run_query failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def scale_up_instance(db_instance_identifier: str, confirm: bool = False) -> str:
    """Scale the RDS instance up to the next larger instance class.

    This modifies the live DB instance. The confirm parameter must be set to
    true by the operator before this tool will execute the change.

    Args:
        db_instance_identifier: The RDS DB instance identifier to scale up.
        confirm: Must be set to true by the operator to authorise the scale-up.

    Returns:
        Confirmation message or error string.
    """
    if not confirm:
        return (
            "ACTION REQUIRES CONFIRMATION: scaling up will modify the running DB instance "
            "and cause a brief restart. Please confirm by setting confirm=true."
        )
    try:
        instance = _describe_instance(db_instance_identifier)
        current_class = instance["DBInstanceClass"]
        next_class = _next_instance_class(db_instance_identifier, current_class)
        if next_class == "NA":
            return "Unable to determine next instance class — already at the largest available size."
        logger.info("Scaling %s from %s to %s", db_instance_identifier, current_class, next_class)
        rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            DBInstanceClass=next_class,
            ApplyImmediately=True,
        )
        return f"Submitted scale-up request: {db_instance_identifier} {current_class} -> {next_class}"
    except Exception as exc:
        logger.error("scale_up_instance failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def increase_iops(
    db_instance_identifier: str,
    percent_increase: int,
    confirm: bool = False,
) -> str:
    """Increase the provisioned IOPS for the RDS instance by a given percentage.

    This modifies the live DB instance's storage configuration. The confirm
    parameter must be set to true by the operator before this tool will
    execute the change.

    Args:
        db_instance_identifier: The RDS DB instance identifier.
        percent_increase: Percentage by which to increase current IOPS (e.g. 25 means +25%).
        confirm: Must be set to true by the operator to authorise the IOPS increase.

    Returns:
        Confirmation message or error string.
    """
    if not confirm:
        return (
            f"ACTION REQUIRES CONFIRMATION: this will increase provisioned IOPS by "
            f"{percent_increase}% on instance {db_instance_identifier}. "
            "Please confirm by setting confirm=true."
        )
    try:
        instance = _describe_instance(db_instance_identifier)
        current_iops = instance["Iops"]
        allocated_storage = instance["AllocatedStorage"]
        new_iops = current_iops + int(current_iops * percent_increase / 100)
        logger.info("Increasing IOPS for %s: %d -> %d", db_instance_identifier, current_iops, new_iops)
        rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            Iops=new_iops,
            AllocatedStorage=allocated_storage,
            ApplyImmediately=True,
        )
        return (
            f"Submitted IOPS increase request for {db_instance_identifier}: "
            f"{current_iops} -> {new_iops} (+{percent_increase}%)"
        )
    except Exception as exc:
        logger.error("increase_iops failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def increase_storage_size(
    db_instance_identifier: str,
    percent_increase: int,
    confirm: bool = False,
) -> str:
    """Increase the allocated storage size for the RDS instance by a given percentage.

    This modifies the live DB instance. Storage increases are irreversible.
    The confirm parameter must be set to true by the operator before this
    tool will execute the change.

    Args:
        db_instance_identifier: The RDS DB instance identifier.
        percent_increase: Percentage by which to increase allocated storage (e.g. 20 means +20%).
        confirm: Must be set to true by the operator to authorise the storage increase.

    Returns:
        Confirmation message or error string.
    """
    if not confirm:
        return (
            f"ACTION REQUIRES CONFIRMATION: this will increase allocated storage by "
            f"{percent_increase}% on {db_instance_identifier}. Storage increases are "
            "irreversible. Please confirm by setting confirm=true."
        )
    try:
        instance = _describe_instance(db_instance_identifier)
        current_storage = instance["AllocatedStorage"]
        current_iops = instance.get("Iops")
        new_storage = int(current_storage + current_storage * percent_increase / 100)
        kwargs: dict = dict(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=new_storage,
            ApplyImmediately=True,
        )
        if current_iops:
            kwargs["Iops"] = current_iops
        logger.info(
            "Increasing storage for %s: %d GB -> %d GB",
            db_instance_identifier, current_storage, new_storage,
        )
        rds_client.modify_db_instance(**kwargs)
        return (
            f"Submitted storage increase request for {db_instance_identifier}: "
            f"{current_storage} GB -> {new_storage} GB (+{percent_increase}%)"
        )
    except Exception as exc:
        logger.error("increase_storage_size failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


@tool
def increase_acu(
    db_instance_identifier: str,
    percent_increase: int,
    confirm: bool = False,
) -> str:
    """Increase the max ACU (Aurora Capacity Units) for the serverless cluster by a percentage.

    This modifies the Aurora Serverless v2 scaling configuration. The confirm
    parameter must be set to true by the operator before this tool will
    execute the change.

    Args:
        db_instance_identifier: The RDS DB instance identifier in the serverless cluster.
        percent_increase: Percentage by which to increase max ACU (e.g. 50 means +50%).
        confirm: Must be set to true by the operator to authorise the ACU increase.

    Returns:
        Confirmation message or error string.
    """
    if not confirm:
        return (
            f"ACTION REQUIRES CONFIRMATION: this will increase the max ACU for the cluster "
            f"containing {db_instance_identifier} by {percent_increase}%. "
            "Please confirm by setting confirm=true."
        )
    try:
        current_max_acu = _get_max_acu_value(db_instance_identifier)
        new_max_acu = current_max_acu + int(current_max_acu * percent_increase / 100)
        # Guarantee at least a unit increase
        if new_max_acu == current_max_acu:
            new_max_acu += 1
        cluster_id = _get_cluster_name(db_instance_identifier)
        logger.info(
            "Increasing max ACU for cluster %s: %.1f -> %.1f",
            cluster_id, current_max_acu, new_max_acu,
        )
        rds_client.modify_db_cluster(
            DBClusterIdentifier=cluster_id,
            ServerlessV2ScalingConfiguration={"MaxCapacity": new_max_acu},
            ApplyImmediately=True,
        )
        return (
            f"Submitted max ACU increase for cluster {cluster_id}: "
            f"{current_max_acu} -> {new_max_acu} (+{percent_increase}%)"
        )
    except Exception as exc:
        logger.error("increase_acu failed: %s\n%s", exc, traceback.format_exc())
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an expert Aurora PostgreSQL incident-remediation agent.

Your job is to help operators diagnose and resolve database incidents by:
1. Gathering metrics and instance details (always do this first).
2. Recommending a remediation action based on the evidence.
3. Asking the operator to confirm BEFORE executing any mutating action
   (scale_up_instance, increase_iops, increase_storage_size, increase_acu).
4. Executing the confirmed action and reporting the outcome.

Safety rules you must always follow:
- Never run SQL queries that are not SELECT/SHOW/EXPLAIN/WITH.
- Never execute a mutating tool without confirm=True from the operator.
- Always summarise what you found before proposing a fix.
- If uncertain, ask a clarifying question rather than guessing.

Available tools: get_instance_details, get_cpu_metrics, get_iops_metrics,
get_max_acu, run_query, scale_up_instance, increase_iops,
increase_storage_size, increase_acu.
"""


def create_agent() -> Agent:
    """Build and return a configured Strands Agent for incident remediation."""
    model_id = os.environ.get(
        "BEDROCK_MODEL_ID",
        os.environ.get("BEDROCK_CLAUDE_MODEL_ID", "global.anthropic.claude-sonnet-5"),
    )
    model = BedrockModel(
        model_id=model_id,
        region_name=_region,
        temperature=0.0,
        max_tokens=4096,
        streaming=True,
    )
    return Agent(
        model=model,
        tools=[
            get_instance_details,
            get_cpu_metrics,
            get_iops_metrics,
            get_max_acu,
            run_query,
            scale_up_instance,
            increase_iops,
            increase_storage_size,
            increase_acu,
        ],
        system_prompt=_SYSTEM_PROMPT,
    )


if __name__ == "__main__":
    import sys
    agent = create_agent()
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello — what can you help me with?"
    print(str(agent(prompt)))
