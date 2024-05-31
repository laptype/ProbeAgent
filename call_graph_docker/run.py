import base64
import json
import logging
import os

from swe_eval import main as eval_main


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("evaluate_instance")



if __name__ == '__main__':
    assert os.getenv('INSTANCE') is not None, "INSTANCE environment variable is not set"
    assert os.getenv('LOG_DIR') is not None, "LOG_DIR environment variable is not set"
    assert os.getenv('TESTBED_NAME') is not None, "TESTBED_NAME environment variable is not set"

    repo_dir = os.getenv('REPO_DIR')
    if not repo_dir:
        repo_dir = os.getenv('TESTBED')

    assert repo_dir, "REPO_DIR environment variable is not set"

    task_instance = json.loads(base64.b64decode(os.getenv('INSTANCE')).decode('utf-8'))
    output_dir = os.getenv('OUTPUT_DIR')

    template_path = os.path.join(os.getenv('CALL_GRAPH_PATH'), 'template.py')
    debug_function_path = os.path.join(os.getenv('CALL_GRAPH_PATH'), 'debug_function.py')
    eval_main(
        task_instance=task_instance,
        testbed_name=os.getenv('TESTBED_NAME'),
        repo_dir=repo_dir,
        log_dir=os.getenv('LOG_DIR'),
        timeout=int(os.getenv('TIMEOUT')) if os.getenv('TIMEOUT') is not None else None,
        log_suffix=os.getenv('LOG_SUFFIX'),
        image_type=os.getenv('IMAGE_TYPE', 'conda'),
        template_path=template_path,
        debug_function_path=debug_function_path
    )

    # 将 task_instance 写入到 testpy.json 文件中
    with open(os.path.join(output_dir, 'testpy.json'), 'w', encoding='utf-8') as f:
        json.dump(task_instance, f, ensure_ascii=False, indent=4)
