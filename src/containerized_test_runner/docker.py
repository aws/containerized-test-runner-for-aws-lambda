import logging
import json
import subprocess
import requests
import os
import time
import threading
from typing import Dict, List, Union

logging.getLogger("urllib3").propagate = False

from .tester import AssertionEvaluator, ExecutionTestSucceeded, ExecutionTestFailed, Resource, InvalidResource, Response, ErrorResponse, InvalidResourceError
from .driver import Driver
from .models import Request, ConcurrentTest

RUNTIME_HOST_CONNECTION_TIMEOUT = 120
TIMEOUT_FOR_CONTAINER_TO_BE_READY_IN_SECONDS = 5

class DockerDriver(Driver):
    def __init__(self,  args):
        self.logger = logging.getLogger("DockerDriver")
        self.logger.setLevel(logging.DEBUG if args.get("debug") else logging.INFO)
        self.test_image = args.get("test_image")
        self.task_root = args.get("task_root")
        self.entrypoint = args.get("entrypoint")

    def __str__(self):
        return "DockerDriver()"

    def fetch(self, index_suite):
        suite_content = index_suite["index"]
        handler = suite_content["handler"]
        request = self._to_resource_type(suite_content, suite_content.get("request", {}))
        environment_variables = self._to_resource_type(suite_content, {})
        client_context = self._to_resource_type(suite_content, {})
        cognito_identity = self._to_resource_type(suite_content, {})
        xray_trace_info = self._to_resource_type(suite_content, {})
        resp = self._capture(suite_content,
                             handler,
                             request,
                             environment_variables,
                             client_context,
                             cognito_identity,
                             xray_trace_info)
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
                             client_context,
                             cognito_identity,
                             xray_trace_info)

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

    def execute_concurrent(self, concurrent_test: ConcurrentTest):
        """Execute a concurrent test with batches of requests."""
        self.logger.info("execute concurrent test '%s'", concurrent_test.name)
        
        # Start container once for all batches
        container_id = None
        try:
            container_id = self._start_container(concurrent_test.handler, concurrent_test.environment_variables)
            local_address = self._get_local_addr(container_id)
            
            # Wait for container to be ready
            if not self._wait_for_container_ready(local_address):
                raise ExecutionTestFailed(
                    {"name": concurrent_test.name}, 
                    ExecutionTestFailed.COMMAND_FAILED, 
                    "Container failed to become ready"
                )
            
            # Execute each batch
            all_results = []
            for batch_idx, batch in enumerate(concurrent_test.request_batches):
                batch_results = self._execute_batch(batch, local_address, concurrent_test.name, batch_idx)
                all_results.extend(batch_results)
            
            return all_results
            
        finally:
            if container_id:
                if self.logger.isEnabledFor(logging.DEBUG):
                    logs_result = subprocess.run(["docker", "logs", container_id], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    self.logger.debug("docker logs:\n%s", logs_result.stdout.decode())
                docker_kill_cmd = ["docker", "kill", container_id]
                subprocess.run(docker_kill_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                self.logger.debug("Killed container [container_id = {}]".format(container_id))

    def _execute_batch(self, batch: List[Request], local_address: str, test_name: str, batch_idx: int) -> List:
        """Execute a batch of requests concurrently."""
        if len(batch) == 1:
            # Single request - no threading needed
            response = self._execute_single_request(batch[0], local_address)
            return [self._evaluate_request_response(batch[0], response, test_name, batch_idx, 0)]
        
        # Multiple requests - use threading
        response_map: Dict[int, Union[Response, ErrorResponse]] = {}
        
        def execute_request(req_idx: int, request: Request):
            if request.delay:
                time.sleep(request.delay)
            response_map[req_idx] = self._execute_single_request(request, local_address)
        
        threads = []
        for i, request in enumerate(batch):
            t = threading.Thread(target=execute_request, args=(i, request))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Evaluate all responses
        results = []
        for i, request in enumerate(batch):
            response = response_map[i]
            result = self._evaluate_request_response(request, response, test_name, batch_idx, i)
            results.append(result)
        
        return results

    def _execute_single_request(self, request: Request, local_address: str) -> Union[Response, ErrorResponse]:
        """Execute a single request against the container."""
        # Build headers
        headers = {"Content-Type": request.content_type}
        headers.update(request.headers)
        
        if request.client_context:
            headers["Lambda-Runtime-Client-Context"] = json.dumps(request.client_context)
        if request.cognito_identity:
            if 'cognitoIdentityId' in request.cognito_identity:
                headers["Lambda-Runtime-Cognito-Identity-Id"] = request.cognito_identity['cognitoIdentityId']
            if 'cognitoIdentityPoolId' in request.cognito_identity:
                headers["Lambda-Runtime-Cognito-Identity-Pool-Id"] = request.cognito_identity['cognitoIdentityPoolId']
        if request.xray:
            val = "Root={};Parent={};Sampled={}".format(
                request.xray.get('traceId', '1-581cf771-a006649127e371903a2de979'),
                request.xray.get('parentId', 'a794a187a18ff77f'),
                request.xray.get('isSampled', '1')
            )
            headers["Lambda-Runtime-XRay-Trace-Header"] = val
        
        # Encode payload
        if request.content_type == 'application/json':
            req_bytes = json.dumps(request.payload).encode()
        else:
            req_bytes = request.payload if isinstance(request.payload, bytes) else str(request.payload).encode()
        
        # Make request
        response = requests.post(
            url=f"http://{local_address}/2015-03-31/functions/function/invocations",
            data=req_bytes,
            headers=headers
        )
        return self._render_response(response.content)

    def _evaluate_request_response(self, request: Request, response: Union[Response, ErrorResponse], test_name: str, batch_idx: int, req_idx: int):
        """Evaluate a single request's response against its assertions."""
        if not request.assertions:
            return ExecutionTestSucceeded({"name": f"{test_name}_batch{batch_idx}_req{req_idx}"})
        
        try:
            test_context = {"name": f"{test_name}_batch{batch_idx}_req{req_idx}"}
            self.evaluate(test_context, request.assertions, response)
            return ExecutionTestSucceeded(test_context)
        except ExecutionTestFailed as e:
            return e

    def _start_container(self, handler: str, environment_variables: Dict[str, str]) -> str:
        """Start a container and return its ID."""
        extra_docker_args = []
        if self.entrypoint is not None:
            extra_docker_args += ["--entrypoint", self.entrypoint]

        cmd = ["docker", "run", "-d", "-i", "--rm", "-p", "127.0.0.1:0:8080"]

        if self.task_root is not None:
            cmd += ["-v", f"{self.task_root}:/var/task"]

        for key, value in environment_variables.items():
            cmd += ["-e", f"{key}={value}"]

        cmd += extra_docker_args
        cmd += [self.test_image, handler]

        self.logger.debug("cmd to run = %s", cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        container_id = stdout.decode().rstrip()

        if not container_id:
            raise ExecutionTestFailed(
                {"name": "container_start"}, 
                ExecutionTestFailed.COMMAND_FAILED, 
                f"Failed to start container. stderr: {stderr.decode()}"
            )

        return container_id

    def _wait_for_container_ready(self, local_address: str) -> bool:
        """Wait for container to be ready to accept requests."""
        time.sleep(0.1)
        start_time = time.time()
        while time.time() - start_time < TIMEOUT_FOR_CONTAINER_TO_BE_READY_IN_SECONDS:
            try:
                # Simple health check
                response = requests.get(f"http://{local_address}/2015-03-31/functions/function/invocations", timeout=1)
                return True
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                time.sleep(0.5)
        return False

    def _capture(self,
                 test,
                 handler,
                 request,
                 environment_variables,
                 client_context,
                 cognito_identity,
                 xray_trace_info):

        self.logger.info("execute '%s'", test["name"])

        extra_docker_args = []
        if self.entrypoint is not None:
            extra_docker_args += ["--entrypoint", self.entrypoint]

        cmd = ["docker", "run", "-d", "-i", "--rm", "-p", "127.0.0.1:0:8080"]

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

        client_context = client_context.to_json()
        cognito_identity = cognito_identity.to_json()
        xray_trace_info = xray_trace_info.to_json()

        cmd += extra_docker_args
        cmd += [self.test_image, handler]

        headers = {}
        headers["Content-Type"] = request.content_type
        if client_context:
            headers["Lambda-Runtime-Client-Context"] = json.dumps(client_context)
        if 'cognitoIdentityId' in cognito_identity:
            headers["Lambda-Runtime-Cognito-Identity-Id"] = cognito_identity['cognitoIdentityId']
        if 'cognitoIdentityPoolId' in cognito_identity:
            headers["Lambda-Runtime-Cognito-Identity-Pool-Id"] = cognito_identity['cognitoIdentityPoolId']
        if xray_trace_info:
            val = "Root={};Parent={};Sampled={}".format(xray_trace_info['traceId'],
                                                        xray_trace_info['parentId'],
                                                        xray_trace_info['isSampled'])
            headers["Lambda-Runtime-XRay-Trace-Header"] = val

        if request.content_type == 'application/json':
            req_bytes = json.dumps(request.data).encode()
        else:
            req_bytes = request.data

        # Initialize to None so the finally block can safely check if a container
        # was actually started before attempting to fetch logs or kill it.
        container_id = None
        try:
            self.logger.debug("cmd to run = %s", cmd)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            container_id = stdout.decode().rstrip()

            if not container_id:
                raise ExecutionTestFailed(test, ExecutionTestFailed.COMMAND_FAILED, f"Failed to start container. stderr: {stderr.decode()}")

            local_address = self._get_local_addr(container_id)
            response = self._wait_for_container(local_address, req_bytes, headers, TIMEOUT_FOR_CONTAINER_TO_BE_READY_IN_SECONDS)
            if response is None:
                raise ExecutionTestFailed(test, ExecutionTestFailed.COMMAND_FAILED, "Container failed to become ready")
        except subprocess.CalledProcessError as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.COMMAND_FAILED, "Command return code (rc={})".format(e.returncode))
        except Exception as e:
            raise ExecutionTestFailed(test, ExecutionTestFailed.UNKNOWN_ERROR, "Unknown error occurred (e={})".format(e))
        finally:
            if container_id:
                if self.logger.isEnabledFor(logging.DEBUG):
                    logs_result = subprocess.run(["docker", "logs", container_id], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    self.logger.debug("docker logs:\n%s", logs_result.stdout.decode())
                docker_kill_cmd = ["docker", "kill", container_id]
                subprocess.run(docker_kill_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                self.logger.debug("Killed container [container_id = {}]".format(container_id))

        return response

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
        # When running in Docker-in-Docker, use the container's IP address directly
        # First try to get the container's IP address
        docker_inspect_cmd = ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_id]
        docker_inspect_proc = subprocess.Popen(docker_inspect_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        ip_address = docker_inspect_proc.communicate()[0].decode().rstrip()

        if ip_address and ip_address != "":
            return "{}:8080".format(ip_address)

        # Fallback: try docker port (works when running on host)
        docker_port_cmd = ["docker", "port", container_id, "8080"]
        docker_port_proc = subprocess.Popen(docker_port_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        port_output = docker_port_proc.communicate()[0].decode().rstrip()

        self.logger.debug(f"docker port output: '{port_output}'")

        # If docker port returns a valid address, use it
        if port_output and port_output != "":
            return port_output

        # Last resort: try localhost with port 8080
        self.logger.warning("Could not determine container address, using localhost:8080")
        return "127.0.0.1:8080"

    def _wait_for_container(self, local_address, req_bytes, headers, timeout):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.post(url="http://{}/2015-03-31/functions/function/invocations".format(local_address), data=req_bytes, headers=headers)
                response = self._render_response(response.content)
                return response
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        return None