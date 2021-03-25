#!/bin/bash
aws ec2 describe-instances --filters "Name=instance-state-name,Values=pending,running" --query 'Reservations[*].Instances[*].{Name:Name,Instance:InstanceId,InstanceType:InstanceType,InstanceLifecycle:InstanceLifecycle,State:State.Name,IP:PublicIpAddress,DNS:PublicDnsName}'
