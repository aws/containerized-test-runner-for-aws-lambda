import unittest

from lambda_byol_test_harness.tester import AssertionEvaluator, ExecutionTestFailed, Response, ErrorResponse, Resource, InvalidResource


class TestTester(unittest.TestCase):

    FAKE_INVOKE_ID = 'not-a-real-invoke-id'

    def check_passes(self, assertions, value):
        tester = AssertionEvaluator(assertions)
        tester.test("unit_test", value)

    def check_fails_with_type(self, assertions, value, test_failed_type):
        with self.assertRaises(ExecutionTestFailed) as context:
            tester = AssertionEvaluator(assertions)
            tester.test("unit_test", value)

        self.assertEqual(context.exception.type, test_failed_type)

    def test_to_dictionary(self):
        data = {"resource": "test"}
        resource = Resource.from_value(data)
        extracted_data = resource.to_dictionary()
        self.assertEqual(extracted_data, data)

        resource = Resource.from_value("non-dict")
        with self.assertRaises(TypeError):
            resource.to_dictionary()

    def test_invalid_op(self):
        assertions = [{"make-up-operation": "yes"}]
        self.check_fails_with_type(assertions, "hello", ExecutionTestFailed.MISSING_ASSERTION_COMPONENT)
        self.check_fails_with_type(assertions, Response("application/json", {"msg": "yo"}),
                                   ExecutionTestFailed.MISSING_ASSERTION_COMPONENT)

    def test_no_assertion(self):
        assertions = [{}]
        self.check_fails_with_type(assertions, "hello", ExecutionTestFailed.MISSING_ASSERTION_COMPONENT)
        self.check_fails_with_type(assertions, Response("application/json", {"msg": "yo"}),
                                   ExecutionTestFailed.MISSING_ASSERTION_COMPONENT)

    def test_wrong_syntax(self):
        assertions = [{"response": "hello", "contentType": "application/json"}]
        self.check_fails_with_type(assertions, "hello", ExecutionTestFailed.WRONG_ASSERTION_SYNTAX)
        self.check_fails_with_type(assertions, Response("application/json", "hello"),
                                   ExecutionTestFailed.WRONG_ASSERTION_SYNTAX)

    def test_response(self):
        assertions = [{"response": { "msg": "yo" }}]
        self.check_passes(assertions, Response("application/json", { "msg": "yo" }))
        self.check_fails_with_type(assertions, Response("application/json", {"msg": "no"}),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, Response("application/json", {"y": "o"}),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, ErrorResponse({ "errorType": "ErrorInvokeHandler"}, "ErrorInvokeHandler"),
                                   ExecutionTestFailed.RESPONSE_TYPE_MISMATCH)

    def test_error(self):
        assertions = [{"error": { "errorType": "ErrorInvokeHandler", "errorMessage": "Invoke failed" }}]
        self.check_passes(assertions,
                          ErrorResponse({"errorType": "ErrorInvokeHandler", "errorMessage": "Invoke failed"},
                                        "ErrorInvokeHandler"))
        self.check_fails_with_type(assertions, ErrorResponse({"errorType": "UnknownError"},
                                                             "UnknownError"),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, ErrorResponse({"stackTrace": "hello.py, line 15, in <module>"},
                                                             "UnknownError"),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, Response("application/json", {"msg": "yo"}),
                                   ExecutionTestFailed.RESPONSE_TYPE_MISMATCH)

    def test_content_type(self):
        assertions = [{"errorType": "Error.Type"}, {"contentType": "image/png"}]
        self.check_passes(assertions, ErrorResponse("payload", "Error.Type", content_type="image/png"))
        self.check_fails_with_type(assertions, ErrorResponse("payload", "Error.Type", content_type="app/json"), ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, ErrorResponse("payload", "Error.Type"), ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, Response("image/png", "payload"), ExecutionTestFailed.RESPONSE_TYPE_MISMATCH)

        assertions = [{"contentType": "image/png"}]
        self.check_passes(assertions, Response("image/png", {}))
        self.check_passes(assertions, ErrorResponse({}, "Error.Type", "image/png"))

    def test_error_type(self):
        assertions = [{"errorType": "ErrorInvokeHandler"}]
        self.check_passes(assertions, ErrorResponse({ "errorType": "ErrorInvokeHandler" }, "ErrorInvokeHandler"))
        self.check_fails_with_type(assertions, ErrorResponse({"errorType": "UnknownError"}, "UnknownError"),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions,
                                   ErrorResponse({"stackTrace": "hello.py, line 15, in <module>"}, "UnknownError"),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(assertions, Response("application/json", {"msg": "yo"}),
                                   ExecutionTestFailed.RESPONSE_TYPE_MISMATCH)

    def test_transform_response(self):
        response_assertions = [{"transform": ".msg", "response": "yo"}]
        self.check_passes(response_assertions, Response("application/json", {"msg": "yo"}))
        self.check_fails_with_type(response_assertions, Response("application/json", {"msg": "no"}),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(response_assertions, Response("application/json", {"y": "o"}),
                                   ExecutionTestFailed.TRANSFORM_FAILED)

    def test_transform_response_dict(self):
        response_assertions = [{"transform": ".a", "response": "a"}]
        self.check_passes(response_assertions, Response("application/json", {"a": "a", "b": ["b1", "b2"]}))
        response_assertions = [{"transform": "{ a: .a, b: .b }", "response": {"a": "a", "b": ["b1", "b2"]}}]
        self.check_passes(response_assertions, Response("application/json", {"a": "a", "b": ["b1", "b2"]}))

    def test_transform_error_type(self):
        self.check_passes([
            {
                "transform": "if . | contains(\"expected error message\") then \"MatchedError\" else . end",
                "errorType": "MatchedError"
            }],
            ErrorResponse({}, "something with an expected error message"))
        self.check_fails_with_type([
            {
                "transform": "if . | contains(\"expected error message\") then \"MatchedError\" else . end",
                "errorType": "MatchedError"
            }],
            ErrorResponse({}, "something with a surprise error message"),
            ExecutionTestFailed.ASSERTION_FAILED)

    def test_transform_error(self):
        error_assertions = [{"transform": ".errorType", "error": "ErrorInvokeHandler"}]
        self.check_passes(error_assertions,
                          ErrorResponse.from_dictionary("ErrorInvokeHandler",
                                                        {"msg": "yo", "errorType": "ErrorInvokeHandler"}))
        self.check_fails_with_type(error_assertions,
                                   ErrorResponse.from_dictionary("UnknownType",
                                                                 {"msg": "yo", "errorType": "UnknownType"}),
                                   ExecutionTestFailed.ASSERTION_FAILED)
        self.check_fails_with_type(error_assertions,
                                   ErrorResponse.from_dictionary("UnknownType",
                                                                 {"msg": "yo"}),
                                   ExecutionTestFailed.TRANSFORM_FAILED)

    def test_transform_error_bad(self):
        error_assertions = [{"transform": ".missing", "error": "ErrorInvokeHandler"}]
        self.check_fails_with_type(error_assertions,
                                   ErrorResponse.from_dictionary("UnknownType",
                                                                 {"msg": "yo"}),
                                   ExecutionTestFailed.TRANSFORM_FAILED)

        error_assertions = [
          {
            "transform": "if .errorType | contains(\"expected\") then \"matched\" else .errorType end",
            "error": "will-never-match"
          }
        ]
        self.check_fails_with_type(error_assertions,
                                   ErrorResponse.from_dictionary("UnknownType",
                                                                 {"msg": "yo"}),
                                   ExecutionTestFailed.TRANSFORM_FAILED)

    def test_invalid_resource(self):
        data = InvalidResource("FileNotFound for nonexist.json")
        assertions = [{ "response": data }]
        self.check_fails_with_type(assertions, "hello", ExecutionTestFailed.RESOURCE_ERROR)

        data = InvalidResource("FileNotFound for nonexist.json")
        assertions = [{ "error": data }]
        self.check_fails_with_type(assertions,
                                   ErrorResponse({"errorType": "ErrorInvokeHandler", "errorMessage": "Invoke failed"}, "ErrorInvokeHandler"),
                                   ExecutionTestFailed.RESOURCE_ERROR)

        data = InvalidResource("FileNotFound for nonexist.json")
        assertions = [{ "errorType": data }]
        self.check_fails_with_type(assertions,
                                   ErrorResponse({ "errorType": "ErrorInvokeHandler" }, "ErrorInvokeHandler"),
                                   ExecutionTestFailed.RESOURCE_ERROR)
