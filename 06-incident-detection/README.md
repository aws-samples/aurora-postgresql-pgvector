# Lab 06 — Incident Detection and Remediation

This lab builds an end-to-end autonomous incident-management system for Aurora PostgreSQL
using CloudWatch alarms, DynamoDB, a Streamlit UI, Bedrock Knowledge Bases, and a Bedrock
Agent that executes remediation actions.

## What the lab builds

```
CloudWatch alarm
       |
       v
Lambda: cw-ingest-to-dynamodb
       |  (writes alert to DynamoDB)
       v
DynamoDB: cwalerttable_v2
       |
       +-----> Streamlit UI  <----> API Gateway  <----> Lambda: api-get-incidents
       |            |                                    Lambda: api-list-runbook-kb
       |            |                                    Lambda: api-action-runbook-kb
       |            |
       |            v
       |       Bedrock KB (retrieve_and_generate)
       |         knowledge-base/runbooks/*.md
       |
       +-----> Bedrock Agent (invoke_agent)
                   |
                   v
              Lambda: idr-bedrock-agent-action-group
              (RDS scaling / connection draining / parameter changes)
```

## Architecture summary

1. A CloudWatch alarm fires when a database metric (CPU, IOPS, ACU capacity) breaches its
   threshold.
2. The alarm invokes `cw-ingest-to-dynamodb`, which writes an incident record to DynamoDB.
3. The Streamlit UI (secured via Cognito) polls DynamoDB through API Gateway / Lambda and
   displays active incidents.
4. Operators click **Get Runbook** — this calls `api-list-runbook-kb`, which uses Bedrock
   `retrieve_and_generate` against the Knowledge Base to surface relevant runbook steps.
5. Operators click **Auto-Remediate** — this calls `api-action-runbook-kb`, which invokes the
   Bedrock Agent. The agent calls action-group Lambda functions to apply the remediation
   (e.g., modify ACU limits, reboot reader, update parameter group).

> **Note:** mutating agent actions run with `requireConfirmation` DISABLED — this is a
> deliberate workshop simplification so the demo flows end-to-end without human approval
> gates. Do **not** replicate this pattern in production workloads.

## Prerequisites

- Bedrock model access must be enabled in your account/region for:
  - `us.anthropic.claude-haiku-4-5-20251001-v1:0` (runbook KB retrieval)
  - `global.anthropic.claude-sonnet-5` (agent reasoning / list-runbook-steps Lambda)
  - `global.anthropic.claude-sonnet-5` is also available as an override
  - `amazon.titan-embed-text-v2:0` (notebook embeddings — 1024 dimensions)
- Workshop CloudFormation stack deployed (creates Aurora cluster, DynamoDB, Cognito, API
  Gateway, Bedrock Agent, and Knowledge Base).
- Run `script/prereq.sh` in the provisioned workshop environment before starting.

## Environment variables

### Lambda functions

| Variable          | Used by Lambda(s)                               | Description                                                   |
|-------------------|-------------------------------------------------|---------------------------------------------------------------|
| `BEDROCK_MODEL_ID`| `api-list-runbook-kb`, `list-runbook-steps-kb`  | Bedrock model/inference-profile ID (see defaults below)       |
| `KBID`            | `api-list-runbook-kb`, `api-action-runbook-kb`  | Bedrock Knowledge Base ID                                     |
| `CWALERTTABLE`    | `api-list-runbook-kb`, `cw-ingest-to-dynamodb`  | DynamoDB table name (default: `cwalerttable_v2`)              |
| `AGENTID`         | `api-action-runbook-kb`                         | Bedrock Agent ID                                              |
| `AGENT_ALIAS_ID`  | `api-action-runbook-kb`                         | Bedrock Agent alias ID                                        |
| `LOG_LEVEL`       | all Lambdas                                     | Python logging level (default: `INFO`)                        |

Default model IDs (overridable via `BEDROCK_MODEL_ID`):
- `api-list-runbook-kb`: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- `list-runbook-steps-kb`: `global.anthropic.claude-sonnet-5`

### Streamlit UI

| Variable          | Description                                      |
|-------------------|--------------------------------------------------|
| `APIGWURL`        | API Gateway invoke URL                           |
| `APIGWSTAGE`      | API Gateway stage name                           |
| `APP_CLIENT_ID`   | Cognito app client ID                            |
| `USER_POOL_ID`    | Cognito user pool ID                             |
| `AWS_REGION`      | AWS region (default: `us-west-2`)                |
| `DEMO_USERNAME`   | Demo Cognito username (email)                    |
| `DEMO_PASSWORD`   | Demo Cognito password (set by `prereq.sh`)       |

## Two agent implementations

Lab 06 ships two fully functional agent implementations. The **classic Bedrock
Agents** path is the guided workshop flow; the **Strands** path is a modern
code-first alternative added in Phase 3.

### Classic Bedrock Agents (guided lab path)

Located in `lambda/idr-bedrock-agent-action-group-good.py` + the CloudFormation
stack.

- **Managed service:** the agent runtime, tool routing, and multi-turn memory
  are all handled by the Bedrock Agents service; operators interact via
  `invoke_agent`.
- **Tool definition:** a 155-line OpenAPI schema JSON file declares each action;
  a 550-line Lambda function handles all tool dispatch.
- **Session model:** the workshop UI creates a new `uuid1` session ID on every
  call, so context is not preserved between clicks. (A persistent session ID
  would fix this, but it is kept simple for the demo.)
- **Deployment:** Lambda ZIP deployment, IAM execution role, Bedrock Agent
  resource, alias, action group, and Knowledge Base association — all managed
  via CloudFormation.
- **Best for:** production workloads where you want AWS-managed scaling,
  CloudWatch tracing, and the Bedrock Agents governance model.

### Strands Agents (code-first, `strands-agent/`)

Located in [`strands-agent/`](strands-agent/).

- **In-process Python:** the agent runs inside your application process using
  the open-source `strands-agents` SDK. No managed service infrastructure
  required.
- **Tool definition:** ~40-line `@tool` decorated Python functions in
  `agent.py` — docstrings become descriptions, type hints become the JSON
  schema, no separate schema file needed.
- **Session model:** one `Agent` instance per Streamlit browser session kept in
  `st.session_state`. The agent's `.messages` list persists across all turns in
  the session, giving real multi-turn continuity that contrasts directly with
  the classic lab's per-click uuid1 pattern.
- **Streaming:** `agent.stream_async()` yields tokens directly to the UI as
  they arrive.
- **Deployment path:** run locally with `streamlit run app.py`; deploy to
  production via **Bedrock AgentCore**, which hosts Strands agents as a managed
  containerised runtime with the same operational benefits as Bedrock Agents
  (scaling, IAM, versioning) — without any Lambda or schema boilerplate.
- **Best for:** rapid iteration, local development, integration into existing
  Python services, or any scenario where you want the agent logic in source
  control rather than a managed-service configuration.

See [`strands-agent/README.md`](strands-agent/README.md) for setup, IAM
requirements, environment variables, and the safety model (read-only SQL
enforcement, confirm-gated mutations).

## Validation

Before packaging Lambda functions, run:

```bash
find . -type f -name '*.py' -not -path './__pycache__/*' -exec python3 -m py_compile {} +
```

The Lambda handlers expect AWS environment variables and Secrets Manager entries created by
the workshop setup.
