# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test scenarios for multi-concurrency testing."""

from containerized_test_runner.models import Request, ConcurrentTest


def get_test_scenarios():
    """Create test MC scenarios."""
    scenarios = []
    
    # Simple echo test with 2 concurrent requests
    echo_batch = [
        Request.create(
            payload={"message": "hello1"},
            assertions={"response": {"echo": "hello1"}}
        ),
        Request.create(
            payload={"message": "hello2"},
            assertions={"response": {"echo": "hello2"}}
        ),
    ]
    
    scenarios.append(ConcurrentTest(
        name="test_concurrent_echo",
        handler="echo.lambda_handler",
        environment_variables={"AWS_LAMBDA_MAX_CONCURRENCY": "2"},
        request_batches=[echo_batch],
        task_root="test_lambda",
    ))
    
    return scenarios