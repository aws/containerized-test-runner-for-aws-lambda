# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Data models for multi-concurrency test scenarios."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Request:
    """Single request used in concurrent test batches."""
    
    payload: Any
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    content_type: str = "application/json"
    delay: Optional[float] = None
    headers: Dict[str, str] = field(default_factory=dict)
    client_context: Optional[Dict[str, Any]] = None
    cognito_identity: Optional[Dict[str, Any]] = None
    xray: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, payload: Any, assertions: Optional[Dict] = None, **kwargs) -> "Request":
        """Create a Request with normalized assertions."""
        normalized_assertions = []
        if assertions:
            if isinstance(assertions, dict):
                normalized_assertions = [{k: v} for k, v in assertions.items()]
            elif isinstance(assertions, list):
                normalized_assertions = assertions
        
        return cls(payload=payload, assertions=normalized_assertions, **kwargs)


@dataclass
class ConcurrentTest:
    """Multi-concurrency test with batches of concurrent requests."""
    
    name: str
    handler: str
    environment_variables: Dict[str, str]
    request_batches: List[List[Request]]
    image: Optional[str] = None
    task_root: Optional[str] = None
    runtimes: Optional[List[str]] = None