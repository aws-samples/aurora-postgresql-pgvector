ARN=`aws lambda get-function --function-name cw-ingest-to-dynamodb --query Configuration.FunctionArn --output text`
aws cloudwatch delete-alarms --alarm-names cw-acu-alarm
aws cloudwatch put-metric-alarm --alarm-name cw-acu-alarm --alarm-description "apg-idr-acu-node-01 RDS instance is running out of ACU capacity. Fix the issue using runbook" --metric-name ACUUtilization --namespace AWS/RDS --statistic Maximum --period 60 --threshold 75 --comparison-operator GreaterThanThreshold  --dimensions "Name=DBInstanceIdentifier,Value=apg-idr-acu-node-01" --evaluation-periods 1 --alarm-actions ${ARN} --unit Percent --treat-missing-data notBreaching
if [ ${?} -eq 0 ] ; then
    echo "Successfully deployed the CloudWatch alarm for ACU utilization"
else
    echo "Unable to deploy CloudWatch alarm for ACU utilization"
fi
