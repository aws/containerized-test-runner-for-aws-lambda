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
        return "DockerDriver()"

    def fetch(self, index_suite):
        suite_content = index_suite["index"]
        handler = suite_content["handler"]
        hurl_file = suite_content["hurl_file"]
        request = self._to_resource_type(suite_content, suite_content.get("request", {}))
        environment_variables = self._to_resource_type(suite_content, {})
        resp = self._capture(suite_content,
                             handler,
                             request,
                             environment_variables,
                             hurl_file)
        return resp.data

    def execute(self, test):
        test_id = test["name"]

        req = self._to_resource_type(test, test.get("request", {}))
        if not req.content_type:
            req.content_type = 'application/json'

        environment_variables = self._to_resource_type(test, test.get("environmentVariables", {}))

        client_context = self._to_resource_type(test, test.get("clientContext", {}))
        cognito_identity = self._to_resource_type(test, test.get("cognitoIdentity", {}))
        xray_trace_info = self._to_resource_type(test, test.get("xray", {}))

        resp = self._capture(test,
                             test["handler"],
                             req,
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
                 request,
                 environment_variables,
                 hurl_file):

        self.logger.info("execute '%s'", test["name"])

        extra_docker_args = []
        if self.entrypoint is not None:
            extra_docker_args += ["--entrypoint", self.entrypoint]

        cmd = ["docker", "run", "-d", "-i", "--rm", "-p", "0.0.0.0:0:3000", "-e", "AWS_LAMBDA_RUNTIME_API=localhost:9000", "-e", "AWS_LAMBDA_BETA_DEBUG=1"]

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
            print("cmd")
            print(cmd)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            container_id = proc.communicate()[0].decode().rstrip()
            print("my container id is {}", container_id)
            time.sleep(1)
            # sending the init
            init_cmd = ["docker", "exec", container_id, "curl", "-X", "POST", "-H", "Content-Type: application/json", "-d", "{}", "http://localhost:8080/test/init"]
            proc = subprocess.Popen(init_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = proc.communicate()
            # Note: stdout and stderr will be bytes, you might need to decode them
            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
            print(stdout)
            print(stderr)
            print(container_id)

            local_address = self._get_local_addr(container_id)
            print("local address = {}", local_address)
            # hurl command
            hurl_command = ["docker", "run", "--network", "host", "--rm", "-v", "{}/..:/suite".format(self.task_root), self.hurl_image, "--variable", "host={}".format(local_address), "/suite/{}".format(hurl_file)]
            print(hurl_command)
            proc = subprocess.Popen(
                hurl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # This automatically decodes the output
            )
            stdout, stderr = proc.communicate()

            print("Hurl stdout:")
            print(stdout)
            
            print("Hurl stderr:")
            print(stderr)

        


                    
        except subprocess.CalledProcessError as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.COMMAND_FAILED, "Command return code (rc={})".format(e.returncode))
        except Exception as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.UNKNOWN_ERROR, "Unknown error occurred (e={})".format(e))
        finally:
            print("in finally")
            # if self.logger.isEnabledFor(logging.DEBUG):
            print("is enabled")
            subprocess.run(["docker", "logs", container_id])

            # docker_kill_cmd = ["docker", "kill", container_id]
            # subprocess.run(docker_kill_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            # self.logger.debug("Killed container [container_id = {}]".format(container_id))

        return "OK"

    def _to_resource_type(self, test, resource):
        try:
            resource = Resource.from_value(resource)
        except InvalidResourceError as e:
            raise ExecutionTestFailed(test, e.type, str(e))
        return resource

    def _render_response(self, resp):
        try:
            resp = json.loads(resp.decode())
            if "errorType" in resp:
                resp = ErrorResponse(resp, resp["errorType"])
            else:
                resp = Response("application/json", resp)
        except Exception:
            resp = Response("application/unknown", resp)
        return resp

    def _get_local_addr(self, container_id):
        docker_port_cmd = ["docker", "port", container_id, "3000"]
        docker_port_proc = subprocess.Popen(docker_port_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        return docker_port_proc.communicate()[0].decode().rstrip()