## Containerized Test Runner For AWS Lambda

This action runs containerized tests. This is useful for testing how the Runtime Interface Client responds to different events. This action is used by public runtimes.

## Usage

To use this action in your GitHub workflow, add the following step:

```yaml
- name: Run tests
  uses: aws/containerized-test-runner-for-aws-lambda@v1-rc1
  with:
    suiteFileArray: '["./test/suites/*.json"]'
    dockerImageName: 'local/test'
    taskFolder: './test/dockerized/tasks'
```

### Parameters

- `suiteFileArray`: JSON array of glob patterns pointing to test suite files
- `dockerImageName`: Name of the Docker image to use for running tests
- `taskFolder`: Path to the folder containing test task files

## Multi-Concurrency (MC) Test Scenarios

The test runner now supports multi-concurrency test scenarios that can execute multiple requests concurrently against a Lambda container. This is useful for testing concurrent execution behavior, race conditions, and performance under load.

### Usage

Use the `--scenario-dir` option to specify a directory containing Python scenario files:

```bash
python -m containerized_test_runner.cli --test-image my-lambda:latest --scenario-dir ./scenarios
```

### Creating MC Scenarios

Create Python files ending with `_scenarios.py` in your scenario directory:

```python
# my_scenarios.py
from containerized_test_runner.models import Request, ConcurrentTest

def get_my_scenarios():
    """Return list of ConcurrentTest scenarios."""
    
    # Create concurrent requests
    batch = [
        Request.create(
            payload={"message": "hello1"},
            assertions={"response": {"echo": "hello1"}}
        ),
        Request.create(
            payload={"message": "hello2"}, 
            assertions={"response": {"echo": "hello2"}}
        ),
    ]
    
    return [
        ConcurrentTest(
            name="test_concurrent_echo",
            handler="echo.lambda_handler",
            environment_variables={"AWS_LAMBDA_MAX_CONCURRENCY": "2"},
            request_batches=[batch],  # List of batches, each batch runs concurrently
            task_root="test_lambda",
        )
    ]
```

### Request Model

The `Request` class supports:
- `payload`: Request payload (JSON or raw)
- `assertions`: List of assertion dictionaries
- `content_type`: Content type (default: "application/json")
- `delay`: Optional delay before sending request
- `headers`: Additional HTTP headers
- `client_context`, `cognito_identity`, `xray`: Lambda context data

### ConcurrentTest Model

The `ConcurrentTest` class supports:
- `name`: Test scenario name
- `handler`: Lambda handler function
- `environment_variables`: Environment variables for the container
- `request_batches`: List of request batches (each batch executes concurrently)
- `task_root`: Optional task root directory
- `runtimes`: Optional list of supported runtimes

## Current status

This is an alpha release and not yet ready for production use.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

