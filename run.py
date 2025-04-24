import os
import json
import sys

def run_test_command(json_path, docker_image_name):
    """Run the test command for a specific JSON file path."""
    cmd = [
        'python',
        '-m',
        'containerized_test_runner.cli',
        '--test-image',
        docker_image_name,
        '--debug',
        '--task-root',
        '',
        json_path
    ]
    try:
        # Using shell=True because we have '&&' in the command
        result = subprocess.run(' '.join(cmd), shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"Successfully processed {json_path}")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing {json_path}: {e}")
        print(e.stderr)
        return False

def run():
    try:
        # Get the array from the input and parse it
        suite_files_input = os.environ.get('INPUT_SUITE_FILE_ARRAY', '[]')
        suite_files = json.loads(suite_files_input)

        # Get the docker image name
        docker_image_name = os.environ.get('DOCKER_IMAGE_NAME', '')

        if not isinstance(suite_files, list):
            raise ValueError("Input must be a JSON array")

        # Process each file
        success = True
        for file in suite_files:
            if not run_test_command(file, docker_image_name):
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