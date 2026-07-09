#!/usr/bin/bash

PUBLIC_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4 2> /dev/null`
SECURITY_GROUP_ID=$(aws ec2 describe-instances --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

echo ""
echo "You can get your public IP address by visiting https://ifconfig.io/ip"
echo "" 
read -p "Enter your public IP address : " part_ip
echo ${part_ip}

OUTPUT=`aws ec2 authorize-security-group-ingress --group-id ${SECURITY_GROUP_ID}  --protocol tcp --port 8080 --cidr ${part_ip}/32 2>&1`
result=$?

echo "${OUTPUT}" | grep "already exists" > /dev/null
if [ $? -eq 0 -o ${result} -eq 0 ] ; then 
    echo ""
    echo "Please use the following link to access the streamlit application"
    echo ""
    echo "---------------------------"
    echo "http://${PUBLIC_IP}:8080"
    echo "---------------------------"
    echo ""
else
    echo "Unable to update the security group"
    echo "${OUTPUT}"
fi
