import sys

import logging
from constants import PatchType
from context_manager import TaskEnvContextManager
import call_graph_manager as cg
logger = logging.getLogger(__name__)

def main(
    task_instance: dict,
    testbed_name: str,
    repo_dir: str,
    log_dir: str,
    timeout: int,
    log_suffix: str = None,
    image_type: str = 'conda'
):

    logger.info("Instance ID: " + task_instance['instance_id'] + "\nTestbed: " + testbed_name + "\nLog dir: " + log_dir)
    with TaskEnvContextManager(
            task_instance,
            testbed_name,
            repo_dir,
            log_dir,
            timeout=timeout,
            log_suffix=log_suffix,
            image_type=image_type,
    ) as tcm:

        if not tcm.apply_patch(task_instance["test_patch"], patch_type=PatchType.PATCH_TEST.value):
            logger.warning("Evaluation failed")
            sys.exit(1)
        cg_exec = cg.ExecManager(
            exec=tcm.exec,
            task_instance=task_instance,
            testbed_name=testbed_name,
            repo_dir=repo_dir,
            log_dir=log_dir,
            image_type=image_type
        )
        cg.get_call_graph_by_test(
            exec=cg_exec,
            task_id=task_instance['instance_id'],
            test_cmd=task_instance['test_cmd'],
            project_path=repo_dir,
            testcases_failing=task_instance['FAIL_TO_PASS'],
            output_dir=log_dir
        )
        # Run testing script
        if not tcm.run_tests_task(task_instance):
            logger.warning("Evaluation failed")
            sys.exit(1)

        logger.info("Evaluation succeeded")