# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Extended tests for scenario loader edge cases."""

import os
import tempfile
import unittest

from containerized_test_runner.scenario_loader import ScenarioLoader


class TestScenarioLoaderEdgeCases(unittest.TestCase):

    def _write(self, directory, filename, content):
        path = os.path.join(directory, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    # ------------------------------------------------------------------
    # File naming / discovery
    # ------------------------------------------------------------------
    def test_ignores_files_without_scenarios_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "helper.py", "def get_helper_scenarios(): return []")
            self._write(d, "utils_scenarios.py",
                        "from containerized_test_runner.models import Request, ConcurrentTest\n"
                        "def get_util_scenarios():\n"
                        "    return [ConcurrentTest(name='u', handler='h', "
                        "environment_variables={}, request_batches=[[Request.create(payload='x')]])]\n")
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].name, "u")

    # ------------------------------------------------------------------
    # Multiple getter functions in one file
    # ------------------------------------------------------------------
    def test_multiple_getters_in_one_file(self):
        code = (
            "from containerized_test_runner.models import Request, ConcurrentTest\n"
            "def get_alpha_scenarios():\n"
            "    return [ConcurrentTest(name='a', handler='h', "
            "environment_variables={}, request_batches=[[Request.create(payload='1')]])]\n"
            "def get_beta_scenarios():\n"
            "    return [ConcurrentTest(name='b', handler='h', "
            "environment_variables={}, request_batches=[[Request.create(payload='2')]])]\n"
        )
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "multi_scenarios.py", code)
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            names = {s.name for s in scenarios}
            self.assertEqual(names, {"a", "b"})

    # ------------------------------------------------------------------
    # Getter that returns non-list is skipped gracefully
    # ------------------------------------------------------------------
    def test_non_list_return_is_skipped(self):
        code = (
            "def get_bad_scenarios():\n"
            "    return 'not a list'\n"
        )
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "bad_scenarios.py", code)
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            self.assertEqual(scenarios, [])

    # ------------------------------------------------------------------
    # File with syntax error doesn't crash the whole load
    # ------------------------------------------------------------------
    def test_syntax_error_in_file_is_handled(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "broken_scenarios.py", "def get_x_scenarios(\n")  # syntax error
            self._write(d, "good_scenarios.py",
                        "from containerized_test_runner.models import Request, ConcurrentTest\n"
                        "def get_good_scenarios():\n"
                        "    return [ConcurrentTest(name='g', handler='h', "
                        "environment_variables={}, request_batches=[[Request.create(payload='ok')]])]\n")
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].name, "g")

    # ------------------------------------------------------------------
    # Getter that raises is handled gracefully
    # ------------------------------------------------------------------
    def test_getter_that_raises_is_handled(self):
        code = (
            "def get_exploding_scenarios():\n"
            "    raise RuntimeError('boom')\n"
        )
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "exploding_scenarios.py", code)
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            self.assertEqual(scenarios, [])

    # ------------------------------------------------------------------
    # Empty directory returns empty list
    # ------------------------------------------------------------------
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(ScenarioLoader.load_scenarios_from_directory(d), [])

    # ------------------------------------------------------------------
    # Functions not matching get_*_scenarios pattern are ignored
    # ------------------------------------------------------------------
    def test_non_matching_functions_ignored(self):
        code = (
            "from containerized_test_runner.models import Request, ConcurrentTest\n"
            "def make_scenarios():\n"
            "    return [ConcurrentTest(name='no', handler='h', "
            "environment_variables={}, request_batches=[[Request.create(payload='x')]])]\n"
            "def get_real_scenarios():\n"
            "    return [ConcurrentTest(name='yes', handler='h', "
            "environment_variables={}, request_batches=[[Request.create(payload='x')]])]\n"
        )
        with tempfile.TemporaryDirectory() as d:
            self._write(d, "mixed_scenarios.py", code)
            scenarios = ScenarioLoader.load_scenarios_from_directory(d)
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].name, "yes")


if __name__ == "__main__":
    unittest.main()
