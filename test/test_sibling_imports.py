# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test that scenario files can import sibling utility modules."""

import os
import tempfile
import unittest

from containerized_test_runner.scenario_loader import ScenarioLoader


class TestSiblingImports(unittest.TestCase):

    def _write(self, directory, filename, content):
        path = os.path.join(directory, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_scenario_can_import_sibling_module(self):
        """A scenario file can import a helper from the same directory."""
        with tempfile.TemporaryDirectory() as d:
            self._write(
                d,
                "helpers.py",
                (
                    "from containerized_test_runner.models import Request, ConcurrentTest\n"
                    "\n"
                    "def make_test(name):\n"
                    "    return ConcurrentTest(\n"
                    "        name=name,\n"
                    "        handler='h',\n"
                    "        environment_variables={},\n"
                    "        request_batches=[[Request.create(payload='x')]],\n"
                    "    )\n"
                ),
            )
            self._write(
                d,
                "importing_scenarios.py",
                (
                    "from helpers import make_test\n"
                    "\n"
                    "def get_importing_scenarios():\n"
                    "    return [make_test('imported')]\n"
                ),
            )

            scenarios = ScenarioLoader.load_scenarios_from_directory(d)

            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].name, "imported")

    def test_multiple_scenarios_share_same_helper(self):
        """Multiple scenario files can import the same shared helper."""
        with tempfile.TemporaryDirectory() as d:
            self._write(
                d,
                "shared.py",
                (
                    "from containerized_test_runner.models import Request, ConcurrentTest\n"
                    "\n"
                    "def build(name):\n"
                    "    return ConcurrentTest(\n"
                    "        name=name,\n"
                    "        handler='h',\n"
                    "        environment_variables={},\n"
                    "        request_batches=[[Request.create(payload='x')]],\n"
                    "    )\n"
                ),
            )
            self._write(
                d,
                "alpha_scenarios.py",
                "from shared import build\n"
                "def get_alpha_scenarios():\n"
                "    return [build('alpha')]\n",
            )
            self._write(
                d,
                "beta_scenarios.py",
                "from shared import build\n"
                "def get_beta_scenarios():\n"
                "    return [build('beta')]\n",
            )

            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            names = {s.name for s in scenarios}

            self.assertEqual(names, {"alpha", "beta"})

    def test_helper_not_loaded_as_scenario(self):
        """Helper files (not matching *_scenarios.py) are not loaded as scenarios."""
        with tempfile.TemporaryDirectory() as d:
            self._write(
                d,
                "helpers.py",
                (
                    "from containerized_test_runner.models import Request, ConcurrentTest\n"
                    "def get_helper_scenarios():\n"
                    "    return [ConcurrentTest(name='should_not_appear', handler='h', "
                    "environment_variables={}, request_batches=[[Request.create(payload='x')]])]\n"
                ),
            )

            scenarios = ScenarioLoader.load_scenarios_from_directory(d)

            self.assertEqual(scenarios, [])


if __name__ == "__main__":
    unittest.main()
