# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""GitHub Action entrypoint — orchestrates docker builds, networking, and test execution."""

import json
import logging
import os
import subprocess
import sys

from .logger import setup_logger, log_group

logger = logging.getLogger(__name__)

MULTI_CONCURRENCY_NETWORK_NAME = 'multi-concurrent-network'


def is_multi_concurrent():
    return bool(os.environ.get("INPUT_SCENARIO_DIR"))


def run_test_command(json_path, docker_image_name, driver, scenario_dir=None):
    """Run the test command for a specific JSON file path."""
    cmd = [
        'python',
        '-m',
        'containerized_test_runner.cli',
        '--test-image',
        docker_image_name,
        '--debug'
    ]

    if json_path:
        cmd.append(json_path)

    if driver:
        cmd += ['--driver', driver]

    if scenario_dir:
        cmd += ['--scenario-dir', scenario_dir]

    try:
        logger.debug(f"Running: {' '.join(cmd)}")
        sys.stdout.flush()
        result = subprocess.run(cmd, text=True, timeout=600)

        if result.returncode == 0:
            logger.info(f"Successfully processed {json_path}")
            return True
        else:
            logger.error(f"Error processing {json_path}: Return code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 600s: {' '.join(cmd)}")
        return False
    except Exception as e:
        logger.error(f"Error processing {json_path}: {str(e)}")
        return False


def get_required_env_var(var_name):
    """Helper function to get required environment variables"""
    value = os.environ.get(var_name)
    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is not set")
    return value


def _get_container_id():
    """Read the current container ID from /etc/hostname."""
    with open('/etc/hostname') as f:
        return f.read().strip()


def create_network():
    subprocess.run(['docker', 'network', 'create', MULTI_CONCURRENCY_NETWORK_NAME], check=True, capture_output=True)


def attach_to_network(network):
    """Attach the current container to the given Docker network."""
    container_id = _get_container_id()
    if not container_id:
        raise RuntimeError("Could not determine current container ID to attach to network")
    result = subprocess.run(['docker', 'network', 'connect', network, container_id], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to attach to network {network}: {result.stderr}")


def remove_network():
    """Disconnect all containers from the network, then remove it."""
    result = subprocess.run(
        ['docker', 'network', 'inspect', '-f', '{{range .Containers}}{{.Name}} {{end}}', MULTI_CONCURRENCY_NETWORK_NAME],
        capture_output=True, text=True
    )
    for name in result.stdout.split():
        subprocess.run(['docker', 'network', 'disconnect', MULTI_CONCURRENCY_NETWORK_NAME, name], capture_output=True)
    subprocess.run(['docker', 'network', 'rm', MULTI_CONCURRENCY_NETWORK_NAME], check=True, capture_output=True)


def run():
    setup_logger(debug=True)

    try:
        suite_files_input = get_required_env_var('INPUT_SUITE_FILE_ARRAY')
        docker_image_name = get_required_env_var('DOCKER_IMAGE_NAME')
        task_folder = get_required_env_var('TASK_FOLDER')
        github_workspace = get_required_env_var('GITHUB_WORKSPACE')
        driver = os.environ.get('DRIVER')
        scenario_dir = os.environ.get("INPUT_SCENARIO_DIR")
        test_image_with_tasks = f"{docker_image_name}-with-tasks"

        # When multi-concurrency testing is enabled, create a shared network
        # and attach this container to it so it can reach the Lambda containers.
        if is_multi_concurrent():
            create_network()
            attach_to_network(MULTI_CONCURRENCY_NETWORK_NAME)
            os.environ["DOCKER_SHARED_NETWORK"] = MULTI_CONCURRENCY_NETWORK_NAME

        logger.info(f"Building test image with tasks: {test_image_with_tasks}")

        dockerfile_content = f"""FROM {docker_image_name}
COPY {task_folder} /var/task
"""
        dockerfile_path = os.path.join(github_workspace, 'Dockerfile.test-with-tasks')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        build_cmd = ['docker', 'build', '-f', dockerfile_path, '-t', test_image_with_tasks, github_workspace]
        logger.debug(f"Running: {' '.join(build_cmd)}")
        sys.stdout.flush()
        with log_group(f"Docker build: {test_image_with_tasks}"):
            build_result = subprocess.run(build_cmd, text=True, timeout=120)
        if build_result.returncode != 0:
            raise Exception(f"Failed to build test image (exit code {build_result.returncode})")

        logger.info(f"Successfully built {test_image_with_tasks}")

        suite_files = json.loads(suite_files_input)

        if not isinstance(suite_files, list):
            raise ValueError("Input must be a JSON array")

        success = True

        # we go either multiconcurrency or not.
        if is_multi_concurrent():
            try:
                if not run_test_command(None, test_image_with_tasks, driver, scenario_dir=scenario_dir):
                    success = False
            finally:
                remove_network()
            sys.exit(0 if success else 1)

        for file in suite_files:
            if not run_test_command(file, test_image_with_tasks, driver):
                success = False

        # Exit with appropriate status code
        sys.exit(0 if success else 1)

    except json.JSONDecodeError:
        logger.error("Invalid JSON input")
        sys.exit(1)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    run()
