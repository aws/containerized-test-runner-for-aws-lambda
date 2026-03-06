import os
import json
import subprocess
import sys


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
        cmd.append(json_path)   #
    
    if driver:
        cmd += ['--driver', driver]

    if scenario_dir:
        cmd += ['--scenario-dir', scenario_dir]
    
    try:
        # Use Popen to get real-time output
        process = subprocess.Popen(
            ' '.join(cmd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Capture output in real-time
        stdout_output = []
        stderr_output = []
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                print(stdout_line.strip())
                stdout_output.append(stdout_line)
            if stderr_line:
                print(stderr_line.strip(), file=sys.stderr)
                stderr_output.append(stderr_line)
            
            if process.poll() is not None:
                break

        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            print(stdout.strip())
            stdout_output.append(stdout)
        if stderr:
            print(stderr.strip(), file=sys.stderr)
            stderr_output.append(stderr)

        if process.returncode == 0:
            print(f"Successfully processed {json_path}")
            return True
        else:
            print(f"Error processing {json_path}: Return code {process.returncode}")
            return False

    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        return False

def get_required_env_var(var_name):
    """Helper function to get required environment variables"""
    value = os.environ.get(var_name)
    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is not set")
    return value
    
def run():
    try:
        suite_files_input = get_required_env_var('INPUT_SUITE_FILE_ARRAY')
        docker_image_name = get_required_env_var('DOCKER_IMAGE_NAME')
        task_folder = get_required_env_var('TASK_FOLDER')
        github_workspace = get_required_env_var('GITHUB_WORKSPACE')
        driver = os.environ.get('DRIVER')
        scenario_dir= os.environ.get("INPUT_SCENARIO_DIR")
        test_image_with_tasks = f"{docker_image_name}-with-tasks"
        print(f"Building test image with tasks: {test_image_with_tasks}")

        dockerfile_content = f"""FROM {docker_image_name}
COPY {task_folder} /var/task
"""
        dockerfile_path = os.path.join(github_workspace, 'Dockerfile.test-with-tasks')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)


        build_cmd = ['docker', 'build', '-f', dockerfile_path, '-t', test_image_with_tasks, github_workspace]
        print(f"DEBUG: Running: {' '.join(build_cmd)}")
        build_result = subprocess.run(build_cmd, capture_output=True, text=True)
        print(build_result.stdout)
        if build_result.stderr:
            print(build_result.stderr)
        if build_result.returncode != 0:
            raise Exception(f"Failed to build test image: {build_result.stderr}")

        print(f"Successfully built {test_image_with_tasks}")

        # todo change it with suite loader
        suite_files = json.loads(suite_files_input)

        if not isinstance(suite_files, list):
            raise ValueError("Input must be a JSON array")

        success = True
        for file in suite_files:
            if not run_test_command(file, test_image_with_tasks, driver):
                success = False

        if scenario_dir:
            if not run_test_command(None, test_image_with_tasks, driver, scenario_dir=scenario_dir):
                success = False

        # Exit with appropriate status code
        sys.exit(0 if success else 1)

    except json.JSONDecodeError:
        print("Error: Invalid JSON input")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run()