# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for scenario loader."""

import os
import tempfile
import unittest

from containerized_test_runner.scenario_loader import ScenarioLoader
from containerized_test_runner.models import ConcurrentTest, Request


class TestScenarioLoader(unittest.TestCase):
    
    def test_load_scenarios_from_directory(self):
        """Test loading scenarios from a directory."""
        # Create a temporary directory with a scenario file
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario_file = os.path.join(temp_dir, "test_scenarios.py")
            with open(scenario_file, 'w') as f:
                f.write("""
from containerized_test_runner.models import Request, ConcurrentTest

def get_test_scenarios():
    return [
        ConcurrentTest(
            name="test_scenario",
            handler="test.handler",
            environment_variables={"TEST": "value"},
            request_batches=[[Request.create(payload={"test": "data"})]]
        )
    ]
""")
            
            scenarios = ScenarioLoader.load_scenarios_from_directory(temp_dir)
            
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].name, "test_scenario")
            self.assertEqual(scenarios[0].handler, "test.handler")
            self.assertEqual(len(scenarios[0].request_batches), 1)
            self.assertEqual(len(scenarios[0].request_batches[0]), 1)
    
    def test_load_scenarios_from_nonexistent_directory(self):
        """Test loading scenarios from a nonexistent directory."""
        scenarios = ScenarioLoader.load_scenarios_from_directory("/nonexistent/path")
        self.assertEqual(len(scenarios), 0)


if __name__ == '__main__':
    unittest.main()