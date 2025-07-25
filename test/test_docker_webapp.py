import unittest
import os

from containerized_test_runner.docker_webapp import DockerWebAppDriver

class TestDockerWebapp(unittest.TestCase):

    def setUp(self):
        self.docker_webapp = DockerWebAppDriver({})

    def test_convert_json_lines_to_array(self):
        json_lines = '''
        {"name": "test1", "value": 1}
        {"name": "test2", "value": 2}
        {"name": "test3", "value": 3}
        '''
        expected = [
            {"name": "test1", "value": 1},
            {"name": "test2", "value": 2},
            {"name": "test3", "value": 3}
        ]
        result = self.docker_webapp._convert_json_lines_to_array(json_lines)
        self.assertEqual(result, expected)

    def test_convert_json_lines_with_invalid_json(self):
        json_lines = '''
        {"name": "test1", "value": 1}
        invalid json
        {"name": "test2", "value": 2}
        '''
        expected = [
            {"name": "test1", "value": 1},
            {"name": "test2", "value": 2}
        ]
        result = self.docker_webapp._convert_json_lines_to_array(json_lines)
        self.assertEqual(result, expected)

    def test_convert_empty_json_lines(self):
        json_lines = ''
        expected = []
        result = self.docker_webapp._convert_json_lines_to_array(json_lines)
        self.assertEqual(result, expected)
