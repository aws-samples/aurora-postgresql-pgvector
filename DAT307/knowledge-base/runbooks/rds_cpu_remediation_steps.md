# Title
Runbook to remediate RDS CPU Utilization alert

## Issue
PostgreSQL database instance is running out of high CPU utilization.

## Description
This run book provides the step by step instructions to address the high CPU Utilization in the RDS instance.
Follow the instructions in this run book to remediate the high CPU utilization incident.

## Steps

1. Check if the RDS instance is in available state. If the status is available, continue otherwise abort the process.

2. Get the current CPU utilization metrics for the last 1 hour for the RDS instance. . 

3. Check if the maximum CPU utilization from the CPU metrics is above 80% , then scale up the RDS instance to the next availabe instance type.
