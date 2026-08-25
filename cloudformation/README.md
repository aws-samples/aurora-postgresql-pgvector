# CloudFormation

## `genai-pgvector-labs.yml`

Root template for the **Agentic AI, RAG & Vector Search with Aurora PostgreSQL**
workshop. It nests the VPC, Aurora PostgreSQL, Code Editor, SageMaker notebook,
incident-detection, product-catalog, Q Business and text-summarization stacks.

This is a **mirror**. The authoritative copy lives in the workshop content repo
as `static/genai-pgvector-labs.yml`. It is published here so self-paced
participants have a fetchable template: the content repo is not public, and
Workshop Studio does not publish the root template to its assets bucket.

### Self-paced deployment

Deploy in **us-west-2**. This is not a preference — the nested stacks load Lambda
layers from a us-west-2 bucket, and Lambda requires its code bucket to be in the
same region as the function.

```bash
aws cloudformation create-stack \
  --region us-west-2 \
  --stack-name genai-pgvector-workshop \
  --template-url https://raw.githubusercontent.com/aws-samples/aurora-postgresql-pgvector/main/cloudformation/genai-pgvector-labs.yml \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
  --parameters \
    ParameterKey=ParticipantRoleArn,ParameterValue=arn:aws:iam::ACCOUNT_ID:role/YOUR_ROLE \
    ParameterKey=CreateIDC,ParameterValue=no
```

`ParticipantRoleArn` is the only parameter without a working default. Set
`CreateIDC=no` if the account already has an IAM Identity Center instance — an
account can hold only one, and `yes` fails the stack if one exists.

The full walkthrough, including verification and cleanup, is in the workshop
under **Introduction → Prerequisites → Self-Paced Setup**.

Running this in your own account incurs charges of roughly $15-25/day, mostly
Aurora. Delete the stack when finished.
