import unittest
import os
import json

from lambda_byol_test_harness.runner import Runner
from mock_driver import MockDriver

class TestRunner(unittest.TestCase):

    def setUp(self):
        self.runner = Runner(MockDriver(os.path.dirname(os.path.realpath(__file__))), args=None)

    def test_counter(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/multiple_tests_test_suite.json")]
        results = self.runner.run(suite, override=[])

        self.assertEqual(len(results.evaluated), 4)
        self.assertEqual(len(results.succeeded), 1)
        self.assertEqual(len(results.failed), 2)
        self.assertEqual(len(results.skipped), 1)

    def test_load_simple_test_suite(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/simple_test_suite.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["task"], "/tasks/python37.zip")
        self.assertEqual(test["runtime"], "python-3.7")
        self.assertEqual(test["name"], "test_echo")
        self.assertEqual(test["handler"], "core.echo")
        self.assertEqual(test["request"], {"msg": "message"})
        self.assertEqual(test["environmentVariables"], {"TEST_ENVIRONMENT_VARIABLE": "test_env"})
        self.assertEqual(test["assertions"], [{"response": {"msg": "message"}}])

    def test_load_test_suite_with_resources(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/test_suite_with_resources.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["environmentVariables"].data, {"TEST_ENVIRONMENT_VARIABLE": "test_env_external"})
        self.assertEqual(test["environmentVariables"].content_type, "application/json")

    def test_load_test_suite_with_inline_resources(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/test_suite_with_inline_resources.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["environmentVariables"].data, {"TEST_ENVIRONMENT_VARIABLE": "test_env_inline"})
        self.assertEqual(test["environmentVariables"].content_type, "application/json")

    def test_load_test_suite_with_nested_resources(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/test_suite_with_nested_resources.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["environmentVariables"], {"name.ref": "name_env"})

        self.assertEqual(test["assertions"][0]["response"].data, { "msg": "hello world" })
        self.assertEqual(test["assertions"][0]["response"].content_type, "application/json")

        self.assertEqual(test["request"].data, { "msg": "hello world" })
        self.assertEqual(test["request"].content_type, "application/json")

    def test_load_test_suite_with_xray(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/simple_test_suite_with_xray.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["xray"]["traceId"], "TraceId1")
        self.assertEqual(test["xray"]["parentId"], "ParentId1")
        self.assertEqual(test["xray"]["isSampled"], "3")

        suite = [os.path.join(self.runner.driver.test_root, "resources/simple_test_suite_with_empty_xray.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["xray"]["traceId"], "1-581cf771-a006649127e371903a2de979")
        self.assertEqual(test["xray"]["parentId"], "a794a187a18ff77f")
        self.assertEqual(test["xray"]["isSampled"], "1")

    def test_load_test_suite_with_cognito_identity(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/simple_test_suite_with_cognito_identity.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["cognitoIdentity"]["cognitoIdentityId"], "cognito-id:cognito-id-1")
        self.assertEqual(test["cognitoIdentity"]["cognitoIdentityPoolId"], "cognito-pool-id:cognito-pool-id1")

        suite = [os.path.join(self.runner.driver.test_root, "resources/simple_test_suite_with_empty_cognito_identity.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test

        self.assertEqual(test["cognitoIdentity"]["cognitoIdentityId"], "cognito-id:4ab95ea510c14353a7f6da04489c43b8")
        self.assertEqual(test["cognitoIdentity"]["cognitoIdentityPoolId"], "cognito-pool-id:35ab4794a79a4f23947d3e851d3d6578")

    def test_load_templated_test_suite(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/template_test_suite.json")]
        results = self.runner.run(suite, override=[])

        tests = {}
        for res in results.succeeded:
            test = res.test
            tests[test["name"]] = test
            self.assertEqual(test["task"], "/tasks/python.mytask")
            self.assertEqual(test["handler"], "core.echo")
            self.assertEqual(test["request"], {"msg": "message"})
            self.assertEqual(test["environmentVariables"], {"TEST_ENVIRONMENT_VARIABLE": "test_env"})
            self.assertEqual(test["assertions"], [{"response": {"msg": "message"}}])

        # 3xmemory_mb 3xruntime
        # test_echo x 9, test_echo_128mb x 3 test_echo_python-2.7 x 3
        self.assertEqual([
            "test_echo:128mb:python-2.7",
            "test_echo:128mb:python-3.6",
            "test_echo:128mb:python-3.7",
            "test_echo:512mb:python-2.7",
            "test_echo:512mb:python-3.6",
            "test_echo:512mb:python-3.7",
            "test_echo:1024mb:python-2.7",
            "test_echo:1024mb:python-3.6",
            "test_echo:1024mb:python-3.7",
            "test_echo_python27:128mb",
            "test_echo_python27:512mb",
            "test_echo_python27:1024mb",
            "test_echo_512mb:python-2.7",
            "test_echo_512mb:python-3.6",
            "test_echo_512mb:python-3.7"
        ], [r.test["name"] for r in results.succeeded])

        self.assertEqual("python-2.7", tests["test_echo:512mb:python-2.7"]["runtime"])
        self.assertEqual("python-2.7", tests["test_echo_python27:1024mb"]["runtime"])
        self.assertEqual("python-2.7", tests["test_echo_512mb:python-2.7"]["runtime"])
        self.assertEqual("512mb", tests["test_echo:512mb:python-2.7"]["memory"])
        self.assertEqual("512mb", tests["test_echo_python27:512mb"]["memory"])
        self.assertEqual("512mb", tests["test_echo_512mb:python-3.6"]["memory"])

    def test_load_test_suite_with_resource_transormation(self):
        suite = [os.path.join(self.runner.driver.test_root, "resources/test_suite_with_interpreted_resources.json")]
        results = self.runner.run(suite, override=[])
        test = results.succeeded[0].test
        self.assertEqual(test["request"].to_json(), "a"*42)
