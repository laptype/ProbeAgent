import json
import os
import utils
from swebench_docker.constants import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION, MAP_REPO_TO_TEST_FRAMEWORK,
)
from swebench_docker.utils import get_test_directives
class Task:
    """
    Encapsulate everything required to run one task.
    """

    def __init__(
        self, task_counter: str, task_id: str, setup_info: dict, task_info: dict
    ):
        # a counter str, format "1/150", which means first task out of 150
        self.task_counter = task_counter
        # id from the benchmark
        self.task_id = task_id
        # setup_info (Dict): keys: ['repo_path', 'env_name', 'pre_install', 'install','test_cmd']
        self.setup_info = setup_info
        # task_info (Dict): keys: ['base_commit', 'hints_text', 'created_at',
        # 'test_patch', 'repo', 'problem_statement', 'version', 'instance_id',
        # 'FAIL_TO_PASS', 'PASS_TO_PASS', 'environment_setup_commit']
        self.task_info = task_info

def parse_task_list_file(task_list_file: str) -> list[str]:
    """
    Parse the task list file.
    The file should contain one task/instance id per line, without other characters.
    """
    with open(task_list_file) as f:
        task_ids = f.readlines()
    return [x.strip() for x in task_ids]

def get_task_id_list(task_list_file, task_id):
    # check parameters
    all_task_ids = None
    # if task_id is not None and task_list_file is not None:
    #     raise ValueError("Cannot specify both task and task-list.")

    if task_list_file is not None:
        all_task_ids = parse_task_list_file(task_list_file)

    if task_id is not None:
        all_task_ids = [task_id]

    if len(all_task_ids) == 0:
        raise ValueError("No task ids to run.")

    return all_task_ids


class Config:
    windows = True
    project_root_path = ''
    output_dir = ''         # 输出的路径
    setup_map = {}          # setup_map
    tasks_map = {}          # tasks_map
    all_tasks_ids = []       # task 名称的列表
    all_tasks = []           # task 的列表 [Task, ...]
    do_install = False

    def update_config(self,
                      setup_map_file,
                      tasks_map_file,
                      output_dir = '',
                      task_list_file = None,
                      task_id = None):
        # output root path -------------------------------------
        self.output_dir = utils.convert_dir_to_absolute(output_dir)
        utils.create_dir_if_not_exists(self.output_dir)
        # setup map --------------------------------------------
        with open(setup_map_file) as f:
            self.setup_map = json.load(f)
        with open(tasks_map_file) as f:
            self.tasks_map = json.load(f)
        # tasks ------------------------------------------------
        self.all_tasks_ids = get_task_id_list(task_list_file, task_id)
        self.num_tasks = len(self.all_tasks_ids)
        self.update_all_tasks()
        self.project_root_path = os.getcwd()



    def update_all_tasks(self):
        self.all_tasks = []
        for idx, task_id in enumerate(self.all_tasks_ids):
            setup_info = self.setup_map[task_id]
            task_info = self.tasks_map[task_id]
            task = Task(f"{idx + 1}/{self.num_tasks}", task_id, setup_info, task_info)
            self.all_tasks.append(task)
        return self.all_tasks

    def get_task_instances(self):
        task_instances = []

        # Set the relevant data on task_instances
        for idx, task_id in enumerate(self.all_tasks_ids):
            task = self.tasks_map[task_id]

            test_type = MAP_REPO_TO_TEST_FRAMEWORK[task["repo"]]
            test_directives = get_test_directives(task)
            test_cmd = f"{test_type} {' '.join(test_directives)}"

            task_instances.append({
                "repo": task["repo"],
                "version": task["version"],
                "base_commit": task["base_commit"],
                KEY_INSTANCE_ID: task_id,
                KEY_MODEL: 'no-model',
                "test_patch": task["test_patch"],
                "test_directives": test_directives,
                "test_cmd": test_cmd,
                "FAIL_TO_PASS": task['FAIL_TO_PASS']
            })

        task_instances = sorted(task_instances, key=lambda x: x[KEY_INSTANCE_ID])
        return task_instances

    def update_windows_path(self, path):
        if path.startswith('/opt/'):
            new_path = os.path.join(self.project_root_path, 'data', path[len('/opt/'):])
        else:
            new_path = path
        return new_path