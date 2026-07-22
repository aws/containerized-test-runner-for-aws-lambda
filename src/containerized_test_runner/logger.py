# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Logging setup with GitHub Actions annotation support.

When running inside GitHub Actions, log messages are formatted as workflow
commands that produce annotations in the workflow summary.

Reference: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions

Note: Workflow commands (::error::, etc.) are only parsed by GHA when written
directly to the runner's stdout. When running inside a Docker action container,
stdout is forwarded through Docker and GHA should still parse them — but if
annotations don't appear, verify the output isn't being buffered or wrapped.
"""

import logging
import os
import sys
import time
from contextlib import contextmanager

_is_gha = os.environ.get("GITHUB_ACTIONS") == "true"


class GHAFormatter(logging.Formatter):
    """Formatter that emits GHA workflow commands as annotations.

    Mapping:
        DEBUG    → ::debug::        (only visible with ACTIONS_STEP_DEBUG=true)
        INFO     → plain text       (no annotation)
        WARNING  → ::warning::      (yellow annotation in workflow summary)
        ERROR    → ::error::        (red annotation in workflow summary)
    """

    def format(self, record):
        msg = record.getMessage()
        if record.levelno >= logging.ERROR:
            return f"::error::{msg}"
        if record.levelno >= logging.WARNING:
            return f"::warning::{msg}"
        if record.levelno <= logging.DEBUG:
            return f"::debug::{msg}"
        return msg


class DefaultFormatter(logging.Formatter):
    """Standard timestamped formatter for local/non-GHA environments."""

    converter = time.gmtime

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S.%Z",
        )


def setup_logger(debug=False):
    """Configure logging once at startup. GHA-aware."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(GHAFormatter() if _is_gha else DefaultFormatter())
    logging.basicConfig(level=level, handlers=[handler])


def notice(msg: str):
    """Emit a GHA notice annotation (blue info icon) or plain info message."""
    if _is_gha:
        print(f"::notice::{msg}")
    else:
        logging.getLogger(__name__).info(msg)


@contextmanager
def log_group(title: str):
    """Context manager for collapsible log groups (GHA) or section headers (local).

    Usage:
        with log_group("Container logs for test_otel"):
            print(logs_output)
    """
    if _is_gha:
        print(f"::group::{title}")
    else:
        print(f"\n--- {title} ---")
    try:
        yield
    finally:
        if _is_gha:
            print("::endgroup::")
