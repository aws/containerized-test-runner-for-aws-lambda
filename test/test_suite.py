import unittest
import os
from containerized_test_runner.suiteloader import SuiteLoader


class TestSuiteLoader(unittest.TestCase):

    def setUp(self):
        self.resource_root = os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources")

    def test_template(self):
        suite = SuiteLoader.load_suite_from_file(os.path.join(self.resource_root, "template_test_suite.json"))         
        self.assertEqual(suite["name"].split("/")[-1], "template_test_suite.json")
	  
    def test_suite_prefix(self):
        suite = SuiteLoader.load_suite_from_file(os.path.join(self.resource_root, "template_test_suite.json"))         

        suite = SuiteLoader.add_testsuite_prefix(suite, "c5d.metal")        
        self.assertEqual(suite["name"].split("/")[-1], "c5d.metal.template_test_suite.json")

        suite.pop("name",None)
        suite = SuiteLoader.add_testsuite_prefix(suite, "nothing")  
        self.assertEqual(suite.get("name",None), None) 

    def test_generate_tests_with_template(self):

        suite = SuiteLoader.load_suite_from_file(os.path.join(self.resource_root, "template_test_suite.json"))

        res = SuiteLoader.generate_tests(suite)

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
        ], [t["name"] for t in res])