import os
import argparse
import asyncio
from utils.config import Config
import logging
import subprocess
from call_graph_docker.run_docker import run_task_docker

cfg = Config()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_evaluation")

project_root = os.getcwd()

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--setup-map",
        type=str,
        default="/opt/SWE-bench/setup_result/setup_map.json",
        help="Path to json file that contains the setup information of the projects.",
    )
    parser.add_argument(
        "--tasks-map",
        type=str,
        default="/opt/SWE-bench/setup_result/new_tasks_map.json",
        help="Path to json file that contains the tasks information.",
    )
    ## where to store run results
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Path to the directory that stores the run results.",
    )
    ## which tasks to be run
    parser.add_argument(
        "--task-list-file",
        type=str,
        default='tasks.txt',
        help="Path to the file that contains all tasks ids to be run.",
    )
    ## single task
    # parser.add_argument(
    #     "--task",
    #     type=str,
    #     default="matplotlib__matplotlib-22835",
    #     help="Task id to be run.",
    # )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Task id to be run.",
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=1,
        help="Task id to be run.",
    )
    args = parser.parse_args()
    return args

async def main(args):
    call_graph_docker_path = os.path.join(project_root, 'call_graph_docker')
    entrypoint = os.path.join(call_graph_docker_path, 'entrypoint.sh')

    call_graph_docker_path = str(call_graph_docker_path)
    entrypoint = str(entrypoint)

    # 先执行 chmod 命令
    chmod_command = ['chmod', '+x', entrypoint]
    # 使用 subprocess.run 来执行命令
    result = subprocess.run(chmod_command, check=True, capture_output=True, text=True)

    cfg.windows = False
    # args.task = 'astropy__astropy-11693'
    cfg.update_config(
        setup_map_file=args.setup_map,
        tasks_map_file=args.tasks_map,
        output_dir=args.output_dir,
        task_list_file=args.task_list_file,
        task_id=args.task,
    )
    cfg.do_install = True
    fail_tasks_list = []
    # 创建一个信号量，限制并发任务数量
    num_processes = args.num_processes

    task_instances = cfg.get_task_instances()

    sem = asyncio.Semaphore(num_processes if num_processes > 0 else len(task_instances))

    async with asyncio.TaskGroup() as tg:
        for task in task_instances:
            async def run_task_with_semaphore(task):
                async with sem:
                    try:
                        await run_task_docker(task, cfg.output_dir, 'aorwall', entrypoint, call_graph_docker_path)
                    except Exception as e:
                        print('fail: ', task.task_id)
                        fail_tasks_list.append(task.task_id)

            tg.create_task(run_task_with_semaphore(task))

    print(fail_tasks_list)


if __name__ == '__main__':
    args = get_parser()
    asyncio.run(main(args))
