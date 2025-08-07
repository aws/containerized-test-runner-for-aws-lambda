import logging

from .driver import Driver
from .suiteloader import SuiteLoader
from .tester import ExecutionTestFailed, ExecutionTestSkipped, InvalidResource


class ExecutionTestResults:
    def __init__(self, suite={}):
        self.suite = suite
        self.evaluated = []
        self.succeeded = []
        self.skipped = []
        self.failed = []
        self.failed_names = []


class Runner:
    logger = logging.getLogger("Runner")

    def __init__(self, driver, args):
        self.driver = Driver.load(driver, args)

    def __enter__(self):
        self.driver.setup()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.driver.teardown()

    def load_suite_from_file(self, path):
        """load_suite_from_file is moved to SuiteLoader"""
        return SuiteLoader.load_suite_from_file(path)

    def run(self, suites, override):

        self.logger.info("run with driver %s", self.driver)

        suites = [SuiteLoader.load_suite_from_file(f) for f in suites]

        test_results = ExecutionTestResults()

        for suite in suites:
            try:
                self.run_suite(suite, override, test_results)
            finally:
                self.driver.cleanup(suite)

        return test_results

    def run_suite(self, suite, override, test_results):

        test_default, test_resources = self._get_test_macros(suite, override)
        test_template = suite.get("template", None)
        test_assertions = suite.get("assertions", [])

        # fetch test suite through index suite
        if "index" in suite:
            SuiteLoader.apply_defaults(suite["index"], test_default)
            self.driver.prepare(suite)
            suite = self.driver.fetch(suite)
            suite_default, test_resources = self._get_test_macros(suite, override)
            # The index default will override the suite default
            SuiteLoader.apply_defaults(test_default, suite_default)
        else:
            self.driver.prepare(suite)

        tests = suite["tests"]

        if test_template is not None:
            tests = SuiteLoader.expand_template(test_template, tests)

        for t in tests:
            self._render_test(t, test_resources, test_default, test_assertions)
            try:
                test_results.evaluated.append(t)
                test_succeeded = self.driver.execute(t)
                test_results.succeeded.append(test_succeeded)
            except ExecutionTestFailed as tf:
                self.logger.warning(str(tf))
                test_results.failed.append(tf)
                test_results.failed_names.append(t.get("name", "''"))
            except ExecutionTestSkipped as ts:
                self.logger.warning(str(ts))
                test_results.skipped.append(ts)

    @classmethod
    def summarize_results(cls, results):
        print(
            "{} test(s) executed. {} skipped. {} successful, {} failed".format(
                len(results.evaluated),
                len(results.skipped),
                len(results.succeeded),
                len(results.failed),
            )
        )

        for te in results.failed:
            print("  - {}".format(te.test))

    def _get_test_macros(self, suite, override):
        test_default = suite.get("default", {})
        for k in override:
            self.logger.debug("overriding '%s' with '%s'", k, override[k])
            test_default[k] = override[k]
        test_resources = suite.get("resources", {})
        for resource_key in test_resources:
            resource = test_resources[resource_key]
            test_resources[resource_key] = self.driver.load_resource_data(resource)
        return test_default, test_resources

    XRAY_DEFAULT = {
        "traceId": "1-581cf771-a006649127e371903a2de979",
        "parentId": "a794a187a18ff77f",
        "isSampled": "1",
    }

    COGNITO_IDENTITY_DEFAULT = {
        "cognitoIdentityId": "cognito-id:4ab95ea510c14353a7f6da04489c43b8",
        "cognitoIdentityPoolId": "cognito-pool-id:35ab4794a79a4f23947d3e851d3d6578",
    }

    FORMAT_MAP = {"xray": XRAY_DEFAULT, "cognitoIdentity": COGNITO_IDENTITY_DEFAULT}

    def _render_test(self, test, resources, defaults, glob_assertions):
        SuiteLoader.apply_defaults(test, defaults)
        # filling resources to test
        self._fill_resource(test, resources)
        test["assertions"] += glob_assertions
        for assertion in test["assertions"]:
            self._fill_resource(assertion, resources)

        # format necessary content
        for k in self.FORMAT_MAP:
            if k in test:
                SuiteLoader.apply_defaults(test[k], self.FORMAT_MAP[k])

    def _fill_resource(self, v, resources):
        # Substitute the first level dictionary keys with .ref
        for key in dict(v):
            if key.endswith(".ref"):
                if v[key] not in resources:
                    v[key] = InvalidResource("Resource not found!")
                else:
                    v[key] = resources[v[key]]
                v[key.split(".")[0]] = v.pop(key)
