# Incident Detection and Remediation

This module contains the incident detection and remediation demo assets:

- `notebooks/`: pgvector and visualization notebooks.
- `lambda/`: Lambda action-group handlers.
- `script/`: workshop setup and update scripts.
- `ui/`: Streamlit UI for incident workflows.
- `knowledge-base/`: runbooks and source documents for Bedrock Knowledge Bases.

## Setup Notes

This module depends on AWS resources created by the workshop infrastructure, including Aurora PostgreSQL, Lambda, Cognito, API Gateway, CloudWatch alarms, Bedrock Agents, and Knowledge Bases. Start with `script/prereq.sh` in the provisioned workshop environment.

## Validation

Before packaging Lambda functions, run:

```bash
find . -type f -name '*.py' -not -path './__pycache__/*' -exec python3 -m py_compile {} +
```

The Lambda handlers expect AWS environment variables and Secrets Manager entries created by the workshop setup.
