#!/bin/bash

# 确保工作目录和输出目录有适当的权限a
#chmod -R u+rw $WORKDIR || echo "Warning: Failed to change permissions for $WORKDIR"
#python -m swebench_docker.evaluate_instance
pip install astor
python "$CALL_GRAPH_PATH/run.py"
#echo "Evaluation succeeded"
