# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the logger module — GHA annotations and log_group."""

import logging
import os
import unittest
from io import StringIO
from unittest.mock import patch

from containerized_test_runner import logger as logger_module
from containerized_test_runner.logger import (
    DefaultFormatter,
    GHAFormatter,
    log_group,
    notice,
    setup_logger,
)


class TestGHAFormatter(unittest.TestCase):

    def setUp(self):
        self.formatter = GHAFormatter()

    def _make_record(self, level, msg):
        record = logging.LogRecord(
            name="test", level=level, pathname="", lineno=0,
            msg=msg, args=None, exc_info=None,
        )
        return record

    def test_error_produces_error_annotation(self):
        result = self.formatter.format(self._make_record(logging.ERROR, "something broke"))
        self.assertEqual(result, "::error::something broke")

    def test_warning_produces_warning_annotation(self):
        result = self.formatter.format(self._make_record(logging.WARNING, "watch out"))
        self.assertEqual(result, "::warning::watch out")

    def test_debug_produces_debug_annotation(self):
        result = self.formatter.format(self._make_record(logging.DEBUG, "verbose info"))
        self.assertEqual(result, "::debug::verbose info")

    def test_info_produces_plain_text(self):
        result = self.formatter.format(self._make_record(logging.INFO, "normal message"))
        self.assertEqual(result, "normal message")


class TestDefaultFormatter(unittest.TestCase):

    def test_includes_level_and_name(self):
        formatter = DefaultFormatter()
        record = logging.LogRecord(
            name="test-harness", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=None, exc_info=None,
        )
        result = formatter.format(record)
        self.assertIn("INFO", result)
        self.assertIn("test-harness", result)
        self.assertIn("hello", result)


class TestNotice(unittest.TestCase):

    @patch.object(logger_module, "_is_gha", True)
    def test_notice_in_gha_prints_annotation(self):
        with patch("builtins.print") as mock_print:
            notice("all good")
            mock_print.assert_called_once_with("::notice::all good")

    @patch.object(logger_module, "_is_gha", False)
    def test_notice_outside_gha_logs_info(self):
        with patch("logging.Logger.info") as mock_info:
            notice("all good")
            mock_info.assert_called_once_with("all good")


class TestLogGroup(unittest.TestCase):

    @patch.object(logger_module, "_is_gha", True)
    def test_log_group_in_gha(self):
        with patch("builtins.print") as mock_print:
            with log_group("My Section"):
                pass
            calls = [c[0][0] for c in mock_print.call_args_list]
            self.assertEqual(calls, ["::group::My Section", "::endgroup::"])

    @patch.object(logger_module, "_is_gha", False)
    def test_log_group_outside_gha(self):
        with patch("builtins.print") as mock_print:
            with log_group("My Section"):
                pass
            calls = [c[0][0] for c in mock_print.call_args_list]
            self.assertEqual(calls[0], "\n--- My Section ---")


class TestSetupLogger(unittest.TestCase):

    def setUp(self):
        # Clear all handlers so basicConfig can add ours
        logging.root.handlers.clear()

    def tearDown(self):
        logging.root.handlers.clear()

    @patch.object(logger_module, "_is_gha", False)
    def test_setup_logger_default_uses_default_formatter(self):
        setup_logger(debug=False)
        our_handlers = [
            h for h in logging.root.handlers
            if isinstance(h.formatter, DefaultFormatter)
        ]
        self.assertEqual(len(our_handlers), 1)
        self.assertEqual(logging.root.level, logging.INFO)

    @patch.object(logger_module, "_is_gha", True)
    def test_setup_logger_gha_uses_gha_formatter(self):
        setup_logger(debug=True)
        our_handlers = [
            h for h in logging.root.handlers
            if isinstance(h.formatter, GHAFormatter)
        ]
        self.assertEqual(len(our_handlers), 1)
        self.assertEqual(logging.root.level, logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
