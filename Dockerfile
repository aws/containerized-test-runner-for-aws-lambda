FROM python:3.14-slim

# Copy Docker CLI from the official image (pinned version, no curl | sh)
COPY --from=docker:27.5.1-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app

# Copy the test runner source
COPY . /app

# Install the test runner (pip auto-downloads hatchling as the build backend)
RUN pip install --no-cache-dir .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
