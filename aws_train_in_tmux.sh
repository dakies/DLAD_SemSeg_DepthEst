#!/bin/bash
tmux new-session -d -s dlad -n train
tmux send-keys -t dlad:train "cd ~/code && bash aws_train.sh" Enter
