import asyncio
import base64
import json
import logging
import subprocess
import time

from os.path import join as pjoin
from utils import create_dir_if_not_exists

logger = logging.getLogger(__name__)

import utils
from swebench_docker.constants import MAP_VERSION_TO_INSTALL

def setup_task_floder(output_dir, task_id):
    """Set up the task environment and return the task output directory."""
    # start_time = datetime.datetime.now()
    # start_time_s = start_time.strftime("%Y-%m-%d_%H-%M-%S")
    task_output_dir = pjoin(output_dir, task_id)
    create_dir_if_not_exists(task_output_dir)
    return task_output_dir

async def run_task_docker(task: dict,
                          output_dir: str = '',
                          namespace: str = 'aorwall',
                          entrypoint: str = '/root/code/probe_code_docker/call_graph/entrypoint.sh',
                          call_graph_docker_path: str = '/root/code/probe_code_docker/call_graph_docker',
                          container_log_dir='/output',
                          call_graph_code_dir = '/call_graph',
                          ):

    task_output_dir = setup_task_floder(output_dir, task['instance_id'])
    repo_name = task['repo'].replace("/", "_")

    # 设置主机上的目录权限
    chmod_output_dir_command = ['chmod', '-R', '777', task_output_dir]
    # 使用 subprocess.run 来执行命令
    result = subprocess.run(chmod_output_dir_command, check=True, capture_output=True, text=True)

    # Base64 encode the instance JSON to be sure it can be passed as an environment variable
    instance_b64 = base64.b64encode(json.dumps(task).encode('utf-8')).decode('utf-8')

    specifications = MAP_VERSION_TO_INSTALL[task["repo"]][task["version"]]
    image_prefix = "swe-bench"

    if specifications.get("instance_image", False):
        docker_image = f"{namespace}/{image_prefix}-{repo_name}-instance:{task['instance_id']}"
    else:
        docker_image = f"{namespace}/{image_prefix}-{repo_name}-testbed:{task['version']}"

    docker_command = [
        'docker', 'run',
        '--rm',
        '--privileged',
        '--entrypoint', '/entrypoint.sh',
        '-v', f'{entrypoint}:/entrypoint.sh',  # 挂载到根目录
        '-v', f"{task_output_dir}:{container_log_dir}",
        '-v', f"{call_graph_docker_path}:{call_graph_code_dir}",
        '-e', f"CALL_GRAPH_PATH={call_graph_code_dir}",
        '-e', f"INSTANCE={instance_b64}",
        '-e', f'OUTPUT_DIR={container_log_dir}',
        '-e', f"LOG_DIR={container_log_dir}",
        docker_image
    ]

    cmd_string = ' '.join(docker_command)

    with open(pjoin(task_output_dir, 'cmd.txt'), 'w') as f:
        f.write(cmd_string)

    start_time = time.time()

    try:
        process = await asyncio.create_subprocess_shell(cmd_string, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = await process.communicate()
        stdout = stdout.decode()

        if stderr:
            stderr = stderr.decode()

        elapsed_time = time.time() - start_time

        if process.returncode != 0:
            logger.warning(
                f"[{task['instance_id']}][{docker_image}]  Error running container:")
            logger.warning(f"Command: {cmd_string}")
            logger.warning(f"Stdout - {stdout}")
            logger.warning(f"Stderr - {stderr}")

        elif "succeeded" not in stdout:
            logger.warning(f"[{task['instance_id']}][{docker_image}]  Container ran successfully in {elapsed_time} seconds, but evaluation failed.")
            logger.warning(f"Command: {cmd_string}")
            logger.warning(f"stdout - {stdout}")
        else:
            logger.info(f"[{task['instance_id']}][{docker_image}] Container ran successfully in {elapsed_time} seconds.")

    except Exception as e:
        logger.warning(f"[{task['instance_id']}][{docker_image}]  Error running container: {e}")