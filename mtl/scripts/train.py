import os
import shutil
import uuid

import boto3
from datetime import datetime

import requests
import torch
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger, TestTubeLogger

from aws_start_instance import build_ssh_cmd, build_rsync_cmd
from mtl.experiments.experiment_semseg_with_depth import ExperimentSemsegDepth
from mtl.utils.rules import check_all_rules, pack_submission
from mtl.utils.config import command_line_parser


def main():
    cfg = command_line_parser()
    with open('aws_configs/default_s3_bucket.txt', 'r') as fh:
        S3_BUCKET_NAME = fh.read()
    with open('aws_configs/group_id.txt', 'r') as fh:
        GROUP_ID = int(fh.read())

    # Remove previous logs and check file structure
    if os.path.isdir(cfg.log_dir):
        shutil.rmtree(cfg.log_dir)
    check_all_rules(cfg)

    model = ExperimentSemsegDepth(cfg)

    timestamp = datetime.now().strftime('%m%d-%H%M')
    run_name = f'G{GROUP_ID}_{timestamp}_{cfg.name}_{str(uuid.uuid4())[:5]}'
    tube_logger = TestTubeLogger(
        save_dir=os.path.join(cfg.log_dir),
        name='tube',
        version=0,
    )
    wandb_logger = WandbLogger(
        name=run_name,
        project='DLAD-Ex2',
        save_dir=os.path.join(cfg.log_dir))

    checkpoint_local_callback = ModelCheckpoint(
        dirpath=os.path.join(cfg.log_dir, 'checkpoints'),
        save_last=False,
        save_top_k=1,
        monitor='metrics_summary/grader',
        mode='max',
    )
    s3_log_path = f"s3://{S3_BUCKET_NAME}/{run_name}/"
    checkpoint_s3_callback = ModelCheckpoint(
        dirpath=s3_log_path,
        save_last=False,
        save_top_k=1,
        verbose=True,
        monitor='metrics_summary/grader',
        mode='max',
    )

    # Log AWS instance information to wandb
    ec2_hostname = requests.get('http://169.254.169.254/latest/meta-data/public-hostname').text
    wandb_logger.log_hyperparams({
        "EC2_Hostname": ec2_hostname,
        "EC2_Instance_ID": requests.get('http://169.254.169.254/latest/meta-data/instance-id').text,
        "EC2_SSH": build_ssh_cmd(ec2_hostname),
        "EC2_SSH_Tmux": f"{build_ssh_cmd(ec2_hostname)} -t tmux attach-session -t dlad",
        "EC2_Rsync": build_rsync_cmd(ec2_hostname),
        "S3_Path": s3_log_path,
        "S3_Link": f"https://s3.console.aws.amazon.com/s3/buckets/{S3_BUCKET_NAME}?region=us-east-1&prefix={run_name}/",
        "Group_Id": GROUP_ID
    })

    # Setup training framework
    if cfg.resume is not None and "s3://" in cfg.resume:
        s3 = boto3.resource('s3')
        _, _, resume_bucket_name, resume_bucket_local_path = cfg.resume.split('/', 3)
        resume_bucket = s3.Bucket(resume_bucket_name)
        checkpoints = list(resume_bucket.objects.filter(Prefix=resume_bucket_local_path))
        checkpoints = [c for c in checkpoints if c.key.endswith(".ckpt")]
        if len(checkpoints) != 1:
            print("Your s3 path specification did not match a single checkpoint. Please be more specific:")
            for c in checkpoints:
                print(f"s3://{c.bucket_name}/{c.key}")
            exit()
        else:
            cfg.resume = f"s3://{checkpoints[0].bucket_name}/{checkpoints[0].key}"

    print("Start training", run_name)
    trainer = Trainer(
        logger=[wandb_logger, tube_logger],
        callbacks=[checkpoint_local_callback, checkpoint_s3_callback],
        gpus='-1' if torch.cuda.is_available() else None,
        resume_from_checkpoint=cfg.resume,
        max_epochs=cfg.num_epochs,
        distributed_backend=None,
        weights_summary=None,
        weights_save_path=None,
        num_sanity_val_steps=1,
        # Uncomment the following options if you want to try out framework changes without training too long
        # limit_train_batches=20,
        # limit_val_batches=10,
        # limit_test_batches=10,
        # log_every_n_steps=10,
    )

    if not cfg.prepare_submission:
        trainer.fit(model)

    # prepare submission archive with predictions, source code, training log, and the model
    dir_pred = os.path.join(cfg.log_dir, 'predictions')
    shutil.rmtree(dir_pred, ignore_errors=True)
    trainer.test(model)
    pack_submission(cfg.log_dir, s3_upload_dir=s3_log_path, submission_name=f"submission_{run_name}.zip")


if __name__ == '__main__':
    main()
