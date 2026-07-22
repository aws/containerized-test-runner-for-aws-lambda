"""Entrypoint for the GitHub Action container. Delegates to the package."""
from containerized_test_runner.main import run

if __name__ == "__main__":
    run()
