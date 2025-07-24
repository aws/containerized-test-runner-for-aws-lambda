import logging
import json
import subprocess
import requests
import os
import time

logging.getLogger("urllib3").propagate = False

from .tester import AssertionEvaluator, ExecutionTestSucceeded, ExecutionTestFailed, Resource, InvalidResource, Response, ErrorResponse, InvalidResourceError
from .driver import Driver

class DockerLiteDriver(Driver):
    def __init__(self,  args):
        self.logger = logging.getLogger("DockerDriver")
        self.logger.setLevel(logging.INFO)
        self.test_image = args.get("test_image")
        self.task_root = args.get("task_root")
        self.entrypoint = args.get("entrypoint")
        self.hurl_image = args.get("hurl_image")

    def __str__(self):
        return "DockerLiteDriver()"

    def fetch(self, index_suite):
        suite_content = index_suite["index"]
        handler = suite_content["handler"]
        hurl_file = suite_content["hurl_file"]
        environment_variables = self._to_resource_type(suite_content, {})
        resp = self._capture(suite_content,
                             handler,
                             environment_variables,
                             hurl_file)
        return resp.data

    def execute(self, test):
        test_id = test["name"]
        environment_variables = self._to_resource_type(test, test.get("environmentVariables", {}))

        resp = self._capture(test,
                             test["handler"],
                             environment_variables,
                             test["hurl_file"])

        if "assertions" not in test:
            raise ExecutionTestFailed(test, ExecutionTestFailed.MISSING_ASSERTIONS, "No assertions provided in test {}".format(test_id))

        self.evaluate(test, test["assertions"], resp)
        return ExecutionTestSucceeded(test)

    def fetch_resource_data(self, path):
        resource_path = os.path.join(self.task_root, path)
        with open(resource_path, "rb") as file:
            return file.read()

    def evaluate(self, test, assertions, response):
        tester = AssertionEvaluator(assertions)
        tester.test(test, response)

    def _capture(self,
                 test,
                 handler,
                 environment_variables,
                 hurl_file):

        self.logger.info("execute '%s'", test["name"])

        extra_docker_args = []
        if self.entrypoint is not None:
            extra_docker_args += ["--entrypoint", self.entrypoint]

        cmd = ["docker", "run", "-d", "-i", "--rm", "-p", "0.0.0.0:0:3000", "-e", "AWS_LAMBDA_RUNTIME_API=localhost:9000", "-e", "AWS_LAMBDA_ENTRYPOINT={}".format(handler), "-e", "AWS_LAMBDA_BETA_DEBUG=1"]

        if self.task_root != None:
            cmd += ["-v", "{}:/var/task".format(self.task_root)]

        try:
            environment_variables = environment_variables.to_dictionary()
        except Exception as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.RESOURCE_ERROR, "Unable to convert environment variables to dictionary: {}".format(e))

        for key in environment_variables:
            cmd += [
                "-e",
                "{}={}".format(key, environment_variables[key])
            ]

        cmd += extra_docker_args
        cmd += [self.test_image]
        try:
            self.logger.debug("cmd to run = %s", cmd)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            container_id = proc.communicate()[0].decode().rstrip()
            time.sleep(1)
            # sending the init
            init_cmd = ["docker", "exec", container_id, "curl", "-X", "POST", "-H", "Content-Type: application/json", "-d", "{}", "http://localhost:8080/test/init"]
            proc = subprocess.Popen(init_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.communicate()
            local_address = self._get_local_addr(container_id)
            # hurl command
            hurl_command = ["docker", "run", "--network", "host", "--rm", "-v", "{}/..:/suite".format(self.task_root), self.hurl_image, "--variable", "host={}".format(local_address), "/suite/{}".format(hurl_file)]

            proc = subprocess.Popen(
                hurl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = proc.communicate()
            if "error: Assert" in stderr:
                raise ExecutionTestFailed(test, ExecutionTestFailed.ASSERTION_FAILED, stderr)

        except Exception as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.UNKNOWN_ERROR, "Unknown error occurred (e={})".format(e))
        finally:
            response = subprocess.run(["docker", "logs", container_id], capture_output=True, text=True)
            docker_kill_cmd = ["docker", "kill", container_id]
            subprocess.run(docker_kill_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.debug("Killed container [container_id = {}]".format(container_id))
        response = self._render_response(response.stdout)
        return response

    def _to_resource_type(self, test, resource):
        try:
            resource = Resource.from_value(resource)
        except InvalidResourceError as e:
            raise ExecutionTestFailed(test, e.type, str(e))
        return resource

    def _render_response(self, resp):
        try:
            resp = self._convert_json_lines_to_array(resp)
            if "errorType" in resp:
                resp = ErrorResponse(resp, resp["errorType"])
            else:
                resp = Response("application/json", resp)
        except Exception as e:
            print(e)
            resp = Response("application/unknown", resp)
        return resp

    def _get_local_addr(self, container_id):
        docker_port_cmd = ["docker", "port", container_id, "3000"]
        docker_port_proc = subprocess.Popen(docker_port_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        return docker_port_proc.communicate()[0].decode().rstrip()

    def _convert_json_lines_to_array(self, json_lines: str) -> list:
        result = []
        for line in json_lines.splitlines():
            if line.strip():
                try:
                    json_obj = json.loads(line)
                    result.append(json_obj)
                except json.JSONDecodeError as e:
                    print(f"Error parsing line: {line}")
                    print(f"Error details: {e}")
                    continue
        return result