#!/usr/bin/sh

export AWS_PAGER=""

AGENT_VERSION="DRAFT"
AGENT_ID=$(aws bedrock-agent list-agents --query 'agentSummaries[?agentName==`idr-agent`][agentId]' --output text)
#echo ${AGENT_ID}

ACTION_GROUP_ID=$(aws bedrock-agent list-agent-action-groups --agent-id ${AGENT_ID} --agent-version ${AGENT_VERSION} --query 'actionGroupSummaries[].actionGroupId' --output text )
#echo ${ACTION_GROUP_ID}

ACTION_GROUP_NAME=$(aws bedrock-agent list-agent-action-groups --agent-id ${AGENT_ID} --agent-version ${AGENT_VERSION} --query 'actionGroupSummaries[].actionGroupName' --output text )
#echo ${ACTION_GROUP_NAME}

ACTION_GROUP_EXECUTOR=$(aws bedrock-agent get-agent-action-group --agent-id ${AGENT_ID} --agent-version ${AGENT_VERSION} --action-group-id ${ACTION_GROUP_ID} --query 'agentActionGroup.actionGroupExecutor.lambda' --output text )
#echo ${ACTION_GROUP_EXECUTOR}

ACTION_GROUP_DESC=$(aws bedrock-agent get-agent-action-group --agent-id ${AGENT_ID} --agent-version ${AGENT_VERSION} --action-group-id ${ACTION_GROUP_ID} --query 'agentActionGroup.description' --output text )

aws bedrock-agent update-agent-action-group --agent-id ${AGENT_ID} --agent-version ${AGENT_VERSION} --action-group-id ${ACTION_GROUP_ID} --action-group-name ${ACTION_GROUP_NAME} --action-group-executor lambda=${ACTION_GROUP_EXECUTOR} --function-schema  file://agent_action_group_for_acu.json  --description "${ACTION_GROUP_DESC}" > /dev/null  2>&1

if [ $? -eq 0 ] ; then
    echo "Action group updated successfully. Please prepare the agent with new changes"
else
    echo "Error in updating the action group "
fi




