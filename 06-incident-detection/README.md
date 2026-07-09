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

## Validation

Before packaging Lambda functions, run:

```bash
find . -type f -name '*.py' -not -path './__pycache__/*' -exec python3 -m py_compile {} +
```

The Lambda handlers expect AWS environment variables and Secrets Manager entries created by
the workshop setup.
