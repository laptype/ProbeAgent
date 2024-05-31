import os
import re
import shutil
import logging
import subprocess
from context_manager import ExecWrapper, LogWrapper
from constants import KEY_INSTANCE_ID, PatchType, APPLY_PATCH_FAIL, APPLY_PATCH_PASS, TESTS_FAILED, \
    TESTS_PASSED, TESTS_TIMEOUT, TESTS_ERROR, KEY_MODEL, MAP_VERSION_TO_INSTALL, INSTALL_FAIL
from os.path import join as pjoin
import AddPyCallGraphFail as PyCallGraphCode
import configparser
logger_taskenv = logging.getLogger("taskenv")

class ExecManager:
    def __init__(
        self,
        exec,
        task_instance: dict,
        testbed_name: str,
        repo_dir: str,
        log_dir: str,
        image_type: str = "conda",
    ):
        self.instance_id = task_instance[KEY_INSTANCE_ID]
        self.image_type = image_type
        if image_type == "conda":
            self.cmd_conda_run = f"conda run -n {testbed_name} "
        else:
            self.cmd_conda_run = ""

        self.exec = exec

        self.specifications = MAP_VERSION_TO_INSTALL[task_instance["repo"]][task_instance["version"]]

    def __call__(self, cmd: str):

        if "image" in self.specifications and self.specifications["image"] == "python":
            test_cmd = cmd
        else:
            test_cmd = f"{self.cmd_conda_run} {cmd}"

        out_test = self.exec(
            test_cmd.split(), shell=False, check=False
        )

def extract_py_paths_from_str(test_cmd: str) -> list:
    py_file_regex = r"\b[\w/.\-]+\.py\b"
    py_file_paths = re.findall(py_file_regex, test_cmd)
    return py_file_paths

def extract_py_paths_from_str_django(test_cmd: str) -> list:
    # Split the command into parts
    parts = test_cmd.split()
    # Use a regular expression to match Python module paths
    pattern = re.compile(r'^[a-zA-Z_][\w\.\-]*$')
    # Extract paths and convert to file paths
    py_paths = ['tests' + os.sep + part.replace('.', os.sep) + '.py' for part in parts if pattern.match(part)]

    return py_paths

def change_tox_ini(path, pkgs):
    # 读取现有的 tox.ini 文件
    config = configparser.ConfigParser()
    file_path = pjoin(path, 'tox.ini')
    config.read(file_path)

    # 添加 networkx 依赖项到 testenv 部分
    testenv_deps = config['testenv'].get('deps', '').split('\n')
    for pkg in pkgs:
        if pkg not in testenv_deps:
            testenv_deps.append(pkg)
    config['testenv']['deps'] = '\n'.join(testenv_deps)

    # 将更改写回 tox.ini 文件
    with open(file_path, 'w') as configfile:
        config.write(configfile)

def copy_debug_function(debug_function_path, py_path):
    py_dir = os.path.dirname(py_path)

    # 获取debug_function_path的文件名
    debug_function_filename = os.path.basename(debug_function_path)

    # 构造目标路径
    destination_path = os.path.join(py_dir, debug_function_filename)

    # 复制文件到目标路径
    shutil.copy(debug_function_path, destination_path)

    print(f"File {debug_function_filename} copied to {py_dir}")

def get_call_graph_by_test(
        exec: ExecManager,
        task_id = '',
        test_cmd = '',
        project_path = '',
        testcases_failing=[],
        output_dir='',
        template_path ='',
        debug_function_path = '',
):
    # [1] 提取测试的文件
    if "django" in task_id:
        py_files_list = extract_py_paths_from_str_django(test_cmd)
    else:
        py_files_list = extract_py_paths_from_str(test_cmd)
    # [2] 修改这个测试文件
    pycallgraph_name = 'pycallgraph2'
    # pycallgraph_name = 'pycallgraph2' if utils.check_python_version(self.logger, self.env_name, [3, 6]) else 'pycallgraph'
    py_trans_list = []
    method_filter_list = PyCallGraphCode.get_method_filter(test_cmd, testcases_failing, task_id)
    print(method_filter_list)
    for py_file in py_files_list:
        py_path = pjoin(project_path, py_file)
        print(py_path)
        copy_debug_function(debug_function_path, py_path)
        transformer = PyCallGraphCode.add_pycallgraph_to_file(
            file_path=py_path,
            save_graph_path=output_dir,
            save_graph_png_path=pjoin(output_dir, 'funcCallGraph'),
            max_depth=25,
            task_id=task_id,
            method_filter_list=method_filter_list,
            pycallgraph_name=pycallgraph_name,
            is_save_test_code=True,
            template_path=template_path
        )
        py_trans_list.append(transformer)
    # [3] 安装额外的包：
    if 'tox' in test_cmd:
        change_tox_ini(project_path, ['networkx', pycallgraph_name])
    else:
        other_install_cmd = f"python -m pip install {pycallgraph_name} networkx"
        exec(other_install_cmd)
