#!/bin/bash

# Setup environment (do not change this)
source activate pytorch_p36
pip install -r requirements.txt
export WANDB_API_KEY=$(cat "aws_configs/wandb.key")

# Download dataset (do not change this)
if [ ! -d "/home/ubuntu/miniscapes" ]; then
  echo "Download miniscapes"
  aws s3 cp s3://dlad-miniscapes-2021/miniscapes.zip /home/ubuntu/
  echo "Extract miniscapes"
  unzip /home/ubuntu/miniscapes.zip -d /home/ubuntu/ | awk 'BEGIN {ORS=" "} {if(NR%1000==0)print "."}'
  rm /home/ubuntu/miniscapes.zip
  echo "\n"
fi

# Run training
echo "Start training"
cd /home/ubuntu/code/

# BEGIN YOUR CHANGES HERE
# You can specify the hyperparameters and the experiment name here.
python -m mtl.scripts.train \
  --log_dir /home/ubuntu/results/ \
  --dataset_root /home/ubuntu/miniscapes/ \
  --name Default \
  --optimizer sgd \
  --optimizer_lr 0.01
  # ... you can pass further arguments as specified in utils/config.py

# If you want to run multiple experiments after each other, just call the training script multiple times.
# Don't forget to check if the AWS timeout in aws_start_instances.py is still sufficient.
#  python -m mtl.scripts.train \
#    --log_dir /home/ubuntu/results/ \
#    --dataset_root /home/ubuntu/miniscapes/ \
#    --name Default

# END YOUR CHANGES HERE

# Wait a moment before stopping the instance to give a chance to debug
echo "Terminate instance in 2 minutes. Use Ctrl+C to cancel the termination..."
sleep 2m && bash aws_stop_self.sh
