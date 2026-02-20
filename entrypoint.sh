#!/bin/bash
set -e
# Don't cd to /github/workspace - we need to use HOST_WORKSPACE for volume mounts
python /app/run.py
