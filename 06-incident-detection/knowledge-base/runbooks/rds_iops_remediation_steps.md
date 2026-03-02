# Title
Runbook to remediate RDS IOPS reaching limit

## Issue
PostgreSQL database instance is running out of IOPS provisioned.

## Description
This run book provides the step by step instructions to increase the RDS IOPS if it reaches the provisioned limit.
Follow the instructions in this run book to remediate the issues related to the iops limit.

## Steps

1. Check if the RDS instance is in available state. If the status is available, continue otherwise abort the process.

2. Get the maximum IOPS metrics usage for the last 1 hour for the RDS instance. 

3. Get the provisioned iops of the RDS instance. 

4. Check if the maximum IOPS utilization from the IOPS metrics is 80% of the provisioned IOPS then increase it by 20%.
