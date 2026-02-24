import importlib
import json
import logging
from typing import Any, Dict, List
from .tester import AssertionEvaluator, InvalidResource, Resource
from .jq_utils import apply_jq_transform

class Driver:

    table: Dict[str, List[Any]] = {}
    logger = logging.getLogger("Driver")
    _strict_assertion_syntax = True

    def __init__(self, *, strict_assertion_syntax=True, **kwargs):
        self._strict_assertion_syntax = strict_assertion_syntax

    def __str__(self):
        return repr(self)

    def setup(self):
        """
        One-time driver setup before starting to run
        test suites
        """
        pass  # Nothing to setup by default

    def fetch(self, suite):
        """
        Load test suite from an index entry
        :param suite: index suite
        :return: suite containing the loaded test
        """
        raise Exception("fetch() not implemented")

    def prepare(self, suite):
        """
        Prepare suite execution
        :param suite: test definition
        """
        pass

    def execute(self, test):
        """
        Execute a single test
        :param suite: test definition
        :return: test result
        """
        raise Exception("execute() not implemented")

    def fetch_resource_data(self, path):
        """

        :param path: test resource relative path
        :return: data read from test resource
        """
        raise Exception("fetch_resource_data() not implemented")

    def evaluate(self, test, assertions, response):
        tester = AssertionEvaluator(
            assertions, strict_syntax=self._strict_assertion_syntax
        )
        tester.test(test, response)

    def cleanup(self, suite):
        pass  # By default nothing to clean up

    def teardown(self):
        """
        One-time driver teardown after running
        all test suites
        """
        pass  # Nothing to teardown by default

    # driver will load resources from test_root by default
    def load_resource_data(self, resource):
        # ensure resource has contentType key
        # ensure resource has src or data key
        if "contentType" not in resource:
            return InvalidResource("Missing contentType!")

        if "src" not in resource and "data" not in resource:
            return InvalidResource("Missing src or data!")

        if "src" in resource:
            try:
                data = self.fetch_resource_data(resource["src"])

                if resource["contentType"] == "application/json":
                    try:
                        data = json.loads(data.decode("utf-8"))
                    except Exception as e:
                        return InvalidResource(
                            "Failed to load json file (e={}) (resource_path={})".format(
                                e, resource["src"]
                            )
                        )
            except Exception as e:
                return InvalidResource(
                    "Failed to load resource (e={}) (resource_path={})".format(
                        e, resource["src"]
                    )
                )
        elif "data" in resource:
            data = resource["data"]

        if "transform" in resource:
            try:
                data = apply_jq_transform(resource["transform"], data, return_all=False)
            except Exception as e:
                return InvalidResource(
                    "Failed to transform resource (e={}) (data='{}', transform='{}')".format(
                        e, resource["data"], resource["transform"]
                    )
                )

        return Resource(resource["contentType"], data)

    @classmethod
    def register(cls, driver_name, module_name, class_name):
        cls.table[driver_name] = [module_name, class_name]

    @classmethod
    def load(cls, driver, args):
        if isinstance(driver, Driver):
            return driver
        return cls.load_by_name(driver, args)

    @classmethod
    def load_by_name(cls, driver_name, args):

        driver_def = Driver.table.get(driver_name, None)
        if driver_def is None:
            raise Exception("unknown driver '{}'".format(driver_name))

        (module_name, class_name) = driver_def

        cls.logger.info("Loading driver %s::%s", module_name, class_name)

        try:
            driver_class = getattr(importlib.import_module(module_name), class_name)
            return driver_class(args)
        except Exception as e:
            raise Exception("unable to create driver '{}': {}".format(driver_name, e))
