# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Scenario loader for multi-concurrency test scenarios."""

import importlib.util
import logging
import os
import sys
from typing import List

from .models import ConcurrentTest

logger = logging.getLogger(__name__)


class ScenarioLoader:
    """Loads multi-concurrency test scenarios from Python files."""

    @staticmethod
    def load_scenarios_from_directory(scenario_dir: str) -> List[ConcurrentTest]:
        """Load all scenarios from Python files in a directory."""
        scenarios = []
        
        if not os.path.exists(scenario_dir):
            logger.warning(f"Scenario directory does not exist: {scenario_dir}")
            return scenarios
        
        for filename in os.listdir(scenario_dir):
            if filename.endswith('_scenarios.py'):
                filepath = os.path.join(scenario_dir, filename)
                try:
                    file_scenarios = ScenarioLoader._load_scenarios_from_file(filepath)
                    scenarios.extend(file_scenarios)
                    logger.info(f"Loaded {len(file_scenarios)} scenarios from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load scenarios from {filename}: {e}")
        
        return scenarios

    @staticmethod
    def _load_scenarios_from_file(filepath: str) -> List[ConcurrentTest]:
        """Load scenarios from a single Python file."""
        # Load the module
        spec = importlib.util.spec_from_file_location("scenario_module", filepath)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {filepath}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Add the directory to sys.path temporarily so relative imports work
        scenario_dir = os.path.dirname(filepath)
        if scenario_dir not in sys.path:
            sys.path.insert(0, scenario_dir)
        
        try:
            spec.loader.exec_module(module)
        finally:
            # Remove from sys.path
            if scenario_dir in sys.path:
                sys.path.remove(scenario_dir)
        
        # Look for scenario getter functions
        scenarios = []
        for attr_name in dir(module):
            if attr_name.startswith('get_') and attr_name.endswith('_scenarios'):
                getter_func = getattr(module, attr_name)
                if callable(getter_func):
                    try:
                        file_scenarios = getter_func()
                        if isinstance(file_scenarios, list):
                            scenarios.extend(file_scenarios)
                        else:
                            logger.warning(f"Function {attr_name} did not return a list")
                    except Exception as e:
                        logger.error(f"Error calling {attr_name}: {e}")
        
        return scenarios