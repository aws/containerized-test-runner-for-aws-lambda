import os
import json
import subprocess
import sys

def run_test_command(json_path, docker_image_name, task_folder, driver):
    """Run the test command for a specific JSON file path."""
    cmd = [
        'python',
        '-m',
        'containerized_test_runner.cli',
        '--test-image',
        docker_image_name,
        '--debug',
        '--task-root',
        task_folder,
        json_path
    ]
    if driver:
        cmd += ['--driver', driver]
    
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
        workspace = get_required_env_var('GITHUB_WORKSPACE')

        driver = os.environ.get('DRIVER')

        print(f"DEBUG: GITHUB_WORKSPACE = {workspace}")
        print(f"DEBUG: task_folder = {task_folder}")

        task_folder_absolute = os.path.join(workspace, task_folder)
        print(f"DEBUG: task_folder_absolute = {task_folder_absolute}")
        
        # List the task folder to verify files exist
        print(f"DEBUG: Listing {task_folder_absolute}:")
        try:
            result = subprocess.run(['ls', '-la', task_folder_absolute], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"DEBUG: ls stderr: {result.stderr}")
        except Exception as e:
            print(f"DEBUG: Could not list directory: {e}")
        
        suite_files = json.loads(suite_files_input)

        if not isinstance(suite_files, list):
            raise ValueError("Input must be a JSON array")

        resolved_suite_files = []
        for file in suite_files:
            if not os.path.isabs(file):
                resolved_file = os.path.join(workspace, file)
            else:
                resolved_file = file
            resolved_suite_files.append(resolved_file)
            print(f"DEBUG: Suite file: {file} -> {resolved_file}")

        # Process each file
        success = True
        for file in resolved_suite_files:
            if not run_test_command(file, docker_image_name, task_folder_absolute, driver):
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