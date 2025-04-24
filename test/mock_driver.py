import logging
import os

from containerized_test_runner.driver import Driver
from containerized_test_runner.tester import ExecutionTestSucceeded, ExecutionTestFailed, ExecutionTestSkipped

class MockDriver(Driver):

    def __init__(self, test_root):
        self.logger = logging.getLogger("MockDriver")
        self.test_root = test_root

    def __str__(self):
        return "MockDriver()"

    def execute(self, test):
        if "handler" not in test:
            raise ExecutionTestFailed(test, "Handler name does not exist")

        if test["handler"] == "skip":
            raise ExecutionTestSkipped(test, "Test needs to be skipped")

        if test["handler"] == "error":
            raise ExecutionTestFailed(test, "Test failed")

        return ExecutionTestSucceeded(test)

    def fetch_resource_data(self, path):
        resource_path = os.path.join(self.test_root, path)
        with open(resource_path, "rb") as file:
            return file.read()