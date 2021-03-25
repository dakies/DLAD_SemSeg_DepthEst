# DLAD Exercise 2 

Multitask Semantic Segmentation and Monocular Depth prediction for Autonomous Driving

![Teaser](./doc/teaser.png)
 
This is a template project for the practical assignment #2 in Deep Learning for Autonomous Driving course:
https://www.trace.ethz.ch/teaching/DLAD

Please refer to the assignment PDF for instructions regarding the assignment scope. 

### AWS Setup

If not already done, please follow [doc/AWS_SETUP.md](doc/AWS_SETUP.md) to setup your AWS access.

### AWS Training

You can simply launch a training on an AWS EC2 instance using:

```shell script
python aws_start_instance.py
```

During the first run, the script will ask you for some information such as the wandb token for the setup.
You can attach to the launched tmux session by running the last printed command. If you want to close the connection
but keep the script running, detach from tmux using Ctrl+B and D. After that, you can exit the ssh connection, while
tmux and the training keep running. You can enter the scroll mode using Ctrl+B and [ and exit it with Q. 
In the scroll mode, you can scroll using the arrow keys or page up and down. Tmux has also some other nice features
such as multiple windows or panels (https://www.hamvocke.com/blog/a-quick-and-easy-guide-to-tmux/). Please note
that there is a **timeout** of 24 hours to the instance. If you find that not sufficient, please adjust 
`TIMEOUT = 24  # in hours`
in [aws_start_instance.py](aws_start_instance.py). To check if you are unintentionally using AWS resources, you can
have a look at the AWS cost explorer: https://console.aws.amazon.com/cost-management/home?region=us-east-1#/dashboard.

In order to change the training arguments or run multiple trainings after each other, you can have a look at 
[aws_train.sh](aws_train.sh). This bash script setups your environment and executes the python training script 
[mtl/scripts/train.py](mtl/scripts/train.py). Here is also the place, where you want to specify your hyperparameters
as command line arguments. The default call looks like this:

```shell script
python -m mtl.scripts.train \
  --log_dir /home/ubuntu/results/ \
  --dataset_root /home/ubuntu/miniscapes/ \
  --name Default \
  --optimizer sgd \
  --optimizer_lr 0.01
```

The full description of all command line keys can be found in [config.py](mtl/utils/config.py).

### AWS Interactive Development

During developing your own code, you'll often run into the problem that the training crashes briefly after the start due
to some typo. In order to avoid the overhead of waiting until AWS allows you to start a new instance as well as the
instance setup, you can continue using the same instance for further development. For that purpose cancel the automatic
termination using Ctrl+C. Fix the bug in your local environment and update your AWS files by running the rsync command, 
which was printed by aws_start_instance.py, on your local machine. After that, you can start the training on the AWS 
instance by running:
```shell script
cd ~/code/ && bash aws_train.sh
``` 

For development, feel free to use your additional m5.large instance (10x cheaper than p2.xlarge) by setting

```python
INSTANCE_TYPE = 'm5.large'
```

in [aws_start_instance.py](aws_start_instance.py). It is sufficient to check if a training crashes in the beginning.
However, do NOT use it for regular training because it will be much slower and in total even more expensive than p2.xlarge.
Also, do not keep it running longer than necessary. 
If you want to test changes of the training framework, please have a look at the commented options of the Trainer in 
[mtl/script/train.py](mtl/script/train.py). 

### Weights and Biases Monitoring

You can monitor the training via the wandb web interface https://wandb.ai/home. If you have lost the ec2 instance 
information for a particular (still running) experiment, you can view it by choosing the 
Table panel on the left side and horizontally scroll the columns until you find the EC2 columns. 
You can even use the web interface to stop a run (click on the three dots beside the run name and choose Stop Run). 
After you stopped the run, it'll still do the test predictions and terminate its instance afterwards. If you do not 
stop a run manually, it will terminate it's instance as well after completion.

In the workspace panel, we recommend switching the x-axis to epoch (x icon in the top right corner) for
visualization.
The logged histograms, you can only view if you click on a single run.

### AWS S3 Checkpoints and Submission Zip

To avoid exceeding the free wandb quota, the checkpoints and submission zips are saved to AWS S3. The link is logged
to wandb. You can find it on the dash board (https://wandb.ai/home) in the Table panel (available on the left side)
in the column S3_Link. 

Use the following command to download a submission archive to the local machine:

```shell script
aws s3 cp <s3_link> <local_destination>
```

### Resume Training

If a spot instance was preempted, you can resume a training by providing the resume flag to mtl.scripts.train in 
[aws_train.sh](aws_train.sh). 

```shell script
python -m mtl.scripts.train \
  --log_dir /home/ubuntu/results/ \
  --dataset_root /home/ubuntu/miniscapes/ \
  --name Default \
  --optimizer sgd \
  --optimizer_lr 0.01 \
  --resume s3://BUCKET_NAME/RUN_NAME/
```

To find out the checkpoint path, go to the wandb Table panel (available on the left side) and checkout the column 
S3_Path. Please note that you will continue from the best performing checkpoint, which is not necessarily the last one. 
This can result in an overlap of both runs. Due to randomness, the runs can achieve different performances in the
overlapping range. Also, you should choose "epoch" as x-axis to avoid visualization issues. 

 
