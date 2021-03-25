#!/bin/bash
set -x

INSTANCE_DESC=$(wget -qO- http://169.254.169.254/latest/dynamic/instance-identity/document)

INSTANCE_REGION=$(echo ${INSTANCE_DESC} | python -c "import json,sys; print(json.loads(sys.stdin.read())['region'])")
INSTANCE_ID=$(echo ${INSTANCE_DESC} | python -c "import json,sys; print(json.loads(sys.stdin.read())['instanceId'])")

IS_SPOT=$(aws ec2 describe-instances --output text --region ${INSTANCE_REGION} --filter Name=instance-id,Values=${INSTANCE_ID} --query 'Reservations[0].Instances[0].InstanceLifecycle')

if [ ${IS_SPOT} == "spot" ]; then
   SPOT_FLEET_REQUEST_ID=$(aws ec2 describe-spot-instance-requests --output text --region ${INSTANCE_REGION} --filter Name=instance-id,Values=${INSTANCE_ID} --query SpotInstanceRequests[0].Tags[?Key==\'aws:ec2spot:fleet-request-id\']\|[0].Value)
   if [ ! ${SPOT_FLEET_REQUEST_ID} == "None" ]; then
       aws ec2 cancel-spot-fleet-requests --region ${INSTANCE_REGION} --terminate-instances --spot-fleet-request-ids ${SPOT_FLEET_REQUEST_ID}
   else
       SPOT_REQUEST_ID=$(aws ec2 describe-spot-instance-requests --output text --region ${INSTANCE_REGION} --filter Name=instance-id,Values=${INSTANCE_ID} --query 'SpotInstanceRequests[0].SpotInstanceRequestId')
       aws ec2 cancel-spot-instance-requests --region ${INSTANCE_REGION} --spot-instance-request-ids ${SPOT_REQUEST_ID}
       aws ec2 terminate-instances --region ${INSTANCE_REGION} --instance-ids ${INSTANCE_ID}
   fi
fi

sudo shutdown -h now
