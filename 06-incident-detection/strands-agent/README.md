# Incident Remediation — Strands Agents Implementation

This directory contains a **code-first** reimplementation of the lab 06
incident-remediation agent using the
[Strands Agents SDK](https://github.com/strands-ai/strands-agents) instead of
the managed Bedrock Agents service.

## What it is

The agent monitors and remediates Aurora PostgreSQL performance incidents by:

1. Fetching instance details and CloudWatch metrics to understand the problem.
2. Proposing a remediation action (scale up, increase IOPS, increase storage, increase ACU).
3. Requiring explicit operator confirmation before executing any mutating action.
4. Applying the change and reporting the outcome.

## How it differs from the classic Bedrock Agents implementation

| Dimension | Classic Bedrock Agents (guided lab path) | Strands implementation (this directory) |
|---|---|---|
| **Agent runtime** | Managed AWS Bedrock Agents service | In-process Python via `strands-agents` SDK |
| **Tool definition** | ~150-line function-definition JSON (`agent_action_group_for_acu.json`) + ~630-line Lambda handler | ~40-line `@tool` decorated functions in `agent.py` |
| **Deployment artefacts** | Lambda ZIP, IAM execution role, Bedrock Agent resource, alias, action group, knowledge base association | Single Python file; run anywhere Python runs |
| **Session continuity** | Classic lab re-creates a new `uuid1` session ID on every button click — context is lost | `Agent.messages` persists on the instance; one `Agent` per Streamlit session gives real multi-turn memory |
| **Streaming** | Bedrock `invoke_agent` event stream, buffered in Lambda | `agent.stream_async()` yields tokens directly to the UI |
| **Iteration speed** | Change → redeploy Lambda → update agent alias → test | Change → save file → rerun `streamlit run app.py` |
| **Observability** | CloudWatch Lambda logs + Bedrock Agents trace | Standard Python `logging`; add OpenTelemetry if needed |

### Bedrock AgentCore

When you are ready to move a Strands agent to production, AWS provides
**Bedrock AgentCore** as a fully managed hosting target. AgentCore takes a
Strands `Agent` object (or any Python callable), packages it into a
containerised runtime, and exposes it through the same Bedrock invoke surface
as a managed Bedrock Agent — giving you the operational benefits of the
managed service (scaling, logging, IAM, versioning) without any manual Lambda
or schema boilerplate. See the
[Bedrock AgentCore documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
for deployment instructions.

## Setup

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `AWS_REGION` | No | AWS region (default: `us-west-2`) |
| `BEDROCK_MODEL_ID` | No | Bedrock model/inference-profile ID (default: `global.anthropic.claude-sonnet-5`) |
| `DB_SECRET_NAME` | No | Secrets Manager secret name for DB credentials. If omitted, the pattern `{db_instance_identifier}-agent-secret` is used (matching the workshop setup). |
| `LOG_LEVEL` | No | Python log level (default: `INFO`) |

Create a `.env` file:

```
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-5
DB_SECRET_NAME=my-aurora-instance-agent-secret
```

### IAM permissions

The IAM principal running the agent needs:

```json
{
  "Effect": "Allow",
  "Action": [
    "rds:DescribeDBInstances",
    "rds:DescribeDBClusters",
    "rds:DescribeOrderableDBInstanceOptions",
    "rds:ModifyDBInstance",
    "rds:ModifyDBCluster",
    "cloudwatch:GetMetricData",
    "secretsmanager:GetSecretValue",
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# Interactive CLI (one-shot prompt)
python agent.py "Instance prod-aurora-writer has high CPU. Check the last 2 hours."

# Streamlit chat UI
streamlit run app.py
```

## Safety model

### Read-only SQL

`run_query` enforces two independent layers of read-only protection:

1. **Application layer:** strips SQL comments, extracts the first keyword, and
   rejects anything that is not `SELECT`, `SHOW`, `EXPLAIN`, or `WITH`.
2. **Connection layer:** opens the psycopg v3 connection with
   `default_transaction_read_only=on` and sets `conn.read_only = True`. Any
   DDL or DML that bypasses layer 1 is blocked by the database driver itself.

### Confirm-gated mutations

All tools that modify live infrastructure
(`scale_up_instance`, `increase_iops`, `increase_storage_size`, `increase_acu`)
accept a `confirm: bool` parameter that defaults to `False`. When `confirm` is
`False`, the tool returns a description of what it _would_ do and asks the
operator to call the tool again with `confirm=True`. The agent's system prompt
reinforces this: it must ask the operator before setting `confirm=True`.

This gives operators a human-in-the-loop checkpoint for every destructive
action without requiring any special Bedrock Agents `requireConfirmation`
configuration.
