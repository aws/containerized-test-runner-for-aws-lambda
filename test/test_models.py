# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for multi-concurrency data models."""

import unittest

from containerized_test_runner.models import Request, ConcurrentTest


class TestRequest(unittest.TestCase):

    def test_create_with_dict_assertions(self):
        req = Request.create(payload={"a": 1}, assertions={"response": "ok", "error": "bad"})
        self.assertEqual(req.payload, {"a": 1})
        self.assertEqual(req.assertions, [{"response": "ok"}, {"error": "bad"}])

    def test_create_with_list_assertions(self):
        raw = [{"transform": ".x", "response": "y"}]
        req = Request.create(payload="p", assertions=raw)
        self.assertIs(req.assertions, raw)

    def test_create_with_no_assertions(self):
        req = Request.create(payload="p")
        self.assertEqual(req.assertions, [])

    def test_create_with_empty_dict_assertions(self):
        req = Request.create(payload="p", assertions={})
        self.assertEqual(req.assertions, [])

    def test_create_forwards_kwargs(self):
        req = Request.create(
            payload="p",
            delay=0.5,
            headers={"X-Custom": "val"},
            content_type="text/plain",
        )
        self.assertEqual(req.delay, 0.5)
        self.assertEqual(req.headers, {"X-Custom": "val"})
        self.assertEqual(req.content_type, "text/plain")

    def test_defaults(self):
        req = Request.create(payload="p")
        self.assertEqual(req.content_type, "application/json")
        self.assertIsNone(req.delay)
        self.assertEqual(req.headers, {})
        self.assertIsNone(req.client_context)
        self.assertIsNone(req.cognito_identity)
        self.assertIsNone(req.xray)


class TestConcurrentTest(unittest.TestCase):

    def test_required_fields(self):
        ct = ConcurrentTest(
            name="t", handler="h",
            environment_variables={"K": "V"},
            request_batches=[[Request.create(payload="x")]],
        )
        self.assertEqual(ct.name, "t")
        self.assertIsNone(ct.image)
        self.assertIsNone(ct.task_root)
        self.assertIsNone(ct.runtimes)

    def test_optional_fields(self):
        ct = ConcurrentTest(
            name="t", handler="h",
            environment_variables={},
            request_batches=[],
            image="img:latest",
            task_root="/var/task",
            runtimes=["python3.13"],
        )
        self.assertEqual(ct.image, "img:latest")
        self.assertEqual(ct.task_root, "/var/task")
        self.assertEqual(ct.runtimes, ["python3.13"])


if __name__ == "__main__":
    unittest.main()
