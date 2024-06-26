#!/bin/bash

directory="/root/code/probe_code_docker/test"

echo "$directory"

python main.py \
  --setup-map "/root/code/probe_code_docker/data/setup_map.json" \
  --tasks-map "/root/code/probe_code_docker/data/new_tasks_map.json" \
  --output-dir ${directory} \
  --task-list-file "/root/code/probe_code_docker/tasks.txt" \
  --num_processes 6