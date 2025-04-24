import unittest
import os

from lambda_byol_test_harness.tester import InvalidResource
from mock_driver import MockDriver

class TestDriver(unittest.TestCase):

    def setUp(self):
        self.driver = MockDriver(os.path.dirname(os.path.realpath(__file__)))

    def test_load_resource_data_invalid_resource(self):
        resource = {"url": "/resources/environment_variable.json"}
        resource = self.driver.load_resource_data(resource)
        self.assertIsInstance(resource, InvalidResource)

        resource = {"contentType": "application/json"}
        resource = self.driver.load_resource_data(resource)
        self.assertIsInstance(resource, InvalidResource)

        resource = {"url": "resources/non_exist.json", "contentType": "application/json"}
        resource = self.driver.load_resource_data(resource)
        self.assertIsInstance(resource, InvalidResource)

        resource = {"url": "resources/1meg_payload", "contentType": "application/json"}
        resource = self.driver.load_resource_data(resource)
        self.assertIsInstance(resource, InvalidResource)

    def test_load_resource_json_url(self):
        resource = {"contentType": "application/json", "src": "resources/environment_variable.json"}

        resource = self.driver.load_resource_data(resource)

        self.assertEqual(resource.content_type, "application/json")
        self.assertEqual(resource.data, {"TEST_ENVIRONMENT_VARIABLE": "test_env_external"})

    def test_load_resource_json_inline_data(self):
        resource = {"contentType": "application/json", "data": {"TEST_ENVIRONMENT_VARIABLE": "test_env_inline"}}

        resource = self.driver.load_resource_data(resource)

        self.assertEqual(resource.content_type, "application/json")
        self.assertEqual(resource.data, {"TEST_ENVIRONMENT_VARIABLE": "test_env_inline"})

    def test_load_resource_transfomed_string(self):
        resource = {"contentType": "application/json", "data": "a", "transform": ".*42"}
        resource = self.driver.load_resource_data(resource)

        self.assertEqual(resource.content_type, "application/json")
        self.assertEqual(resource.to_json(), 'a'*42)

    def test_load_resource_python_string(self):
        resource = {"contentType": "application/json", "data": "a", "transform": "Bad expression"}
        resource = self.driver.load_resource_data(resource)

        self.assertTrue(isinstance(resource, InvalidResource))

