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

## Current status

This is an alpha release and not yet ready for production use.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

