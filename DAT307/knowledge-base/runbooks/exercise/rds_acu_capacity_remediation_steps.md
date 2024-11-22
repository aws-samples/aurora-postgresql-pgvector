# Title
Runbook to remediate Aurora Serverless capacity reaching limit

## Issue
PostgreSQL database instance is running at max ACU utilization

## Description
This run book provides the step by step instructions to address the max ACU utilization on Aurora Serverless V2 instance.
Follow the instructions in this run book to remediate the issues related to the Serverless capacity.

## Steps

1. Check if the instance is in available state. If the status is available, continue otherwise abort the process.

2. Get the max ACU allocation for the Aurora instance.

3. Get the current ACU utilization metrics for the last 1 hour for the Aurora instance.

4. Check if the maximum ACU utilization from the ACU metrics is above 80% , then increase the max ACU by 20%.
