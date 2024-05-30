import os

def parse_task_list_file(task_list_file: str) -> list[str]:
    """
    Parse the task list file.
    The file should contain one task/instance id per line, without other characters.
    """
    with open(task_list_file) as f:
        task_ids = f.readlines()
    return [x.strip() for x in task_ids]


def convert_dir_to_absolute(dir_path: str) -> str:
    """
    Convert a (potentially) relative path to an absolute path.
    Args:
        dir_path (str): Path to the directory. Can be relative or absolute.
    Returns:
        str: Absolute path to the directory.
    """
    return os.path.abspath(dir_path)

def create_dir_if_not_exists(dir_path: str):
    """
    Create a directory if it does not exist.
    Args:
        dir_path (str): Path to the directory.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

