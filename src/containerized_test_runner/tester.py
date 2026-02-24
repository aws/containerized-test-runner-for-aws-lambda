import json
import logging
import os
import tempfile
import zipfile
from .jq_utils import apply_jq_transform


class TestResources:
    """
    TestResources that returns only local paths
    """

    def __init__(self, task_root):
        self.task_root = task_root

    def get_url(self, path):
        """
        Return URL to path
        """
        return self.local_path(path)

    def local_path(self, path):
        """
        Return local path to a resource
        """
        # Always make path relative
        return os.path.join(self.task_root, path.lstrip("/"))

    def get_data(self, path):
        resource_path = self.get_url(path)
        with open(resource_path, "rb") as file:
            return file.read()

    def get_test_artifacts_path(self):
        temp_zip_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        self._zip_dir(temp_zip_file.name, self.task_root)
        return temp_zip_file.name

    def _zip_dir(self, zip_file_path, dir_to_zip):
        # Zip test artifacts
        zipf = zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED)

        for root, dirs, files in os.walk(dir_to_zip):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, dir_to_zip))


class ExecutionTestFailed(Exception):
    ASSERTION_FAILED = "assertion-failed"
    MISSING_ASSERTIONS = "missing-assertions"
    MISSING_ASSERTION_COMPONENT = "missing-assertion-component"
    WRONG_ASSERTION_SYNTAX = "wrong-assertion-syntax"
    TRANSFORM_FAILED = "tranform-failed"
    RESOURCE_ERROR = "resource-error"
    COMMAND_FAILED = "command-failed"
    RESPONSE_TYPE_MISMATCH = "response-type-mismatch"
    UNKNOWN_ERROR = "unknown-error"

    def __init__(self, test, type, msg=None, duration=0):
        super(ExecutionTestFailed, self).__init__(msg)
        self.test = test
        self.type = type
        self.msg = msg
        self.duration = duration

    def __str__(self):
        if self.type == self.TRANSFORM_FAILED:
            return f"ExecutionTestFailed(type={self.type}, msg={self.msg})"
        return "ExecutionTestFailed(test={}, type={}, msg={})".format(
            self.test, self.type, self.msg
        )


class ExecutionTestSkipped(Exception):
    def __init__(self, test, reason):
        super(ExecutionTestSkipped, self).__init__(reason)
        self.test = test
        self.reason = reason

    def __str__(self):
        return "ExecutionTestSkipped(test={},reason={})".format(self.test, self.reason)


class ExecutionTestSucceeded:
    def __init__(self, test, duration=0):
        self.test = test
        self.duration = duration

    def __str__(self):
        return "ExecutionTestSucceeded(test={})".format(self.test)


class InvalidResourceError(Exception):

    def __init__(self, data, msg=None):
        super(InvalidResourceError, self).__init__(msg)
        self.data = data
        self.type = ExecutionTestFailed.RESOURCE_ERROR

    def __str__(self):
        return "Invalid resource found in {}".format(self.data)


class Resource:

    def __init__(self, content_type, data):
        self.content_type = content_type
        self.data = data

    def __str__(self):
        return "Resource(ContentType={})".format(self.content_type)

    def to_json(self):
        return self.data

    def to_bytes(self):
        if isinstance(self.data, bytes):
            return self.data
        return json.dumps(self.data).encode()

    def to_dictionary(self):
        if not isinstance(self.data, dict):
            raise TypeError("Cannot convert {} to dictionary".format(type(self.data)))
        return self.data

    @classmethod
    def from_value(cls, resource, content_type=""):
        if content_type is None:
            content_type = ""
        if isinstance(resource, InvalidResource):
            raise InvalidResourceError(resource.data)
        if isinstance(resource, Resource):
            return resource
        return cls(content_type, resource)


class InvalidResource(Resource):

    def __init__(self, data):
        super(InvalidResource, self).__init__(None, data)

    def __str__(self):
        return "InvalidResource"


class Response(Resource):
    def __init__(
        self,
        content_type,
        data,
        metrics={},
        init_metrics={},
        invoke_metrics={},
        customer_logs=None,
    ):
        super(Response, self).__init__(content_type, data)
        self.metrics = metrics
        self.init_metrics = init_metrics
        self.invoke_metrics = invoke_metrics
        self.customer_logs = customer_logs
        self.platform_logs = None

    def __str__(self):
        rendered_data = self.data
        if isinstance(rendered_data, dict):
            rendered_data = json.dumps(rendered_data, indent=2)
        elif rendered_data is not None:
            rendered_data = rendered_data[:1000]
        return "Response(ContentType={})\nData={}\nMetrics:{}\nInitMetrics:{}\nInvokeMetrics:{}\nCustomerLogs:{}\nPlatformLogs:{}".format(
            self.content_type,
            rendered_data,
            self.metrics,
            self.init_metrics,
            self.invoke_metrics,
            self.customer_logs,
            self.platform_logs,
        )


class ErrorResponse(Resource):
    # currently assume all error response data is in json format
    def __init__(
        self,
        data,
        error_type,
        content_type="application/json",
        metrics={},
        init_metrics={},
        invoke_metrics={},
        customer_logs=None,
        request_id=None,
    ):
        super(ErrorResponse, self).__init__(content_type, data)
        self.error_type = error_type
        self.data = data
        self.metrics = metrics
        self.init_metrics = init_metrics
        self.invoke_metrics = invoke_metrics
        self.customer_logs = customer_logs
        self.request_id = request_id
        self.platform_logs = None

    def __str__(self):
        rendered_data = self.data
        if isinstance(rendered_data, dict):
            rendered_data = json.dumps(rendered_data, indent=2)
        elif rendered_data is not None:
            rendered_data = rendered_data[:1000]
        return "ErrorResponse(request_id={}, error_type={}, ContentType={})\nMetrics:{}\nInitMetrics:{}\nInvokeMetrics:{}\nCustomerLogs:{}\nPlatformLogs:{}\nData:\n{}".format(
            self.request_id,
            self.error_type,
            self.content_type,
            self.metrics,
            self.init_metrics,
            self.invoke_metrics,
            self.customer_logs,
            self.platform_logs,
            rendered_data,
        )

    @staticmethod
    def from_dictionary(error_type, data, metadata=None):
        logs = (
            metadata["logs"].split("\n") if (metadata and "logs" in metadata) else None
        )
        metrics = {k: v for k, v in metadata.items() if k != "logs"} if metadata else {}
        return ErrorResponse(data, error_type, metrics=metrics, customer_logs=logs)


class AssertionEvaluator:
    ASSERTION_KEYS = {
        "response",
        "error",
        "responseContentType",
        "contentType",
        "errorType",
        "tail-logs",
        "logs",
        "metrics",
        "init_metrics",
        "invoke_metrics",
    }

    def __init__(self, assertions, *, strict_syntax=True):
        """
        :type assertions: list[dict]
        """
        self.logger = logging.getLogger("AssertionEvaluator")
        self.assertions = assertions
        self._strict_syntax = strict_syntax

    def test(self, test, response):
        to_throw = None
        for assertion in self.assertions:
            self._verify_assertion_syntax(test, assertion)

            if "response" in assertion:
                check_value = self._as_resource(test, assertion["response"])
                assert_value = self._as_type(test, Response, response)

            if "error" in assertion:
                check_value = self._as_resource(test, assertion["error"])
                assert_value = self._as_type(test, ErrorResponse, response)

            if "contentType" in assertion:
                check_value = self._as_resource(test, assertion["contentType"])
                assert_value = self._as_resource(
                    test, self._as_type(test, Resource, response).content_type
                )

            if "responseContentType" in assertion:
                self.logger.warning(
                    "Assertion 'responseContentType' is deprecated, Use 'contentType' instead"
                )
                resource_type = ErrorResponse if "error" in assertion else Response
                check_value = self._as_resource(test, assertion["responseContentType"])
                assert_value = self._as_resource(
                    test, self._as_type(test, resource_type, response).content_type
                )

            if "errorType" in assertion:
                check_value = self._as_resource(test, assertion["errorType"])
                assert_value = self._as_resource(
                    test, self._as_type(test, ErrorResponse, response).error_type
                )

            if "tail-logs" in assertion:
                check_value = self._as_resource(test, assertion["tail-logs"])
                assert_value = self._as_resource(test, response.customer_logs)

            if "logs" in assertion:
                check_value = self._as_resource(test, assertion["logs"])
                assert_value = self._as_resource(test, response.platform_logs)

            if "metrics" in assertion:
                check_value = self._as_resource(test, assertion["metrics"])
                assert_value = self._as_resource(test, response.metrics)

            if "init_metrics" in assertion:
                check_value = self._as_resource(test, assertion["init_metrics"])
                assert_value = self._as_resource(test, response.init_metrics)

            if "invoke_metrics" in assertion:
                check_value = self._as_resource(test, assertion["invoke_metrics"])
                assert_value = self._as_resource(test, response.invoke_metrics)

            if "transform" in assertion:
                transform_method = assertion["transform"]
                assert_value = self._transform(test, assert_value, transform_method)

            try:
                self._compare_values(check_value, assert_value, test)
            except Exception as e:
                self.logger.error("Failed assertion: {}".format(assertion))
                to_throw = to_throw or e

        if to_throw:
            self.logger.error("RESPONSE: {}".format(response))
            raise to_throw

    def _verify_assertion_syntax(self, test, assertion):
        conditions_number = sum(key in assertion for key in self.ASSERTION_KEYS)
        if conditions_number < 1:
            raise ExecutionTestFailed(
                test,
                ExecutionTestFailed.MISSING_ASSERTION_COMPONENT,
                "Must specify one of {} in assertion!".format(self.ASSERTION_KEYS),
            )
        elif conditions_number > 1:
            self.logger.warning(
                "Syntax error in assertion: Must specify one and only one field from the list {} in assertion!"
            )
            if self._strict_syntax:
                raise ExecutionTestFailed(
                    test,
                    ExecutionTestFailed.WRONG_ASSERTION_SYNTAX,
                    "Too many assertion keys found. Provide '--no-strict-assertion-syntax' CLI argument to suppress this error.",
                )

    def _as_type(self, test, response_type, value):
        if not isinstance(value, response_type):
            raise ExecutionTestFailed(
                test,
                ExecutionTestFailed.RESPONSE_TYPE_MISMATCH,
                "Assertion failed. Expected {} but got {}".format(response_type, value),
            )
        return value

    def _as_resource(self, test, value):
        try:
            resource = Resource.from_value(value)
        except InvalidResourceError as e:
            raise ExecutionTestFailed(test, e.type, str(e))
        return resource

    def _compare_values(self, check_value, actual_value, test):
        if actual_value.data != check_value.data:
            raise ExecutionTestFailed(
                test,
                ExecutionTestFailed.ASSERTION_FAILED,
                "Assertion failed. Expected {} but got {}".format(
                    repr(check_value.data), repr(actual_value.data)
                ),
            )

    def _transform(self, test, value, transform_method):
        content_type = value.content_type
        value = value.to_json()
        try:
            transformed_result = apply_jq_transform(transform_method, value, return_all=True)
            # jq transforms a value by JSON script and returns all results as a list.
            # it will return [None] if nothing is returned after transform
            transformed_result = [r for r in transformed_result if r is not None]
            if len(transformed_result) == 0:
                raise Exception("jq transformation returned [None]")
        except Exception as e:
            value_repr = value
            try:
                value_repr = json.dumps(value, indent=2)
            except Exception:
                pass
            raise ExecutionTestFailed(
                test,
                ExecutionTestFailed.TRANSFORM_FAILED,
                "Failed to apply transformation '{}' to the data: '{}'. Error: '{}'".format(
                    transform_method, value_repr, e
                ),
            )

        return Resource.from_value(transformed_result[0], content_type=content_type)

