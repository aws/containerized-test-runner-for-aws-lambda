FROM python:3.14-slim

# Copy uv binary from the official image (pinned version, no remote script execution)
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

# Copy Docker CLI from the official image (pinned version, no curl | sh)
COPY --from=docker:27.5.1-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app

# Copy lockfile and project metadata first (cache layer)
COPY uv.lock pyproject.toml ./

# Copy source
COPY src/ src/
COPY run.py entrypoint.sh conftest.py ./

# Install from lockfile — frozen ensures exact versions, no resolution
RUN uv sync --frozen --no-dev

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
