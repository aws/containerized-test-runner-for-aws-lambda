## Containerized Test Runner For Aws Lambda

This action runs containerized tests. This is useful for testing how the Runtime Interface Client responds to different events. This action is used by public runtimes.

## Current status

This is an alpha release and not yet ready for production use.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.




export INPUT_SUITE_FILE_ARRAY='["./github-action-test/webapp/suite0.json"]'
export DOCKER_IMAGE_NAME='maxday/lite-tester'
export TASK_FOLDER='./github-action-test/webapp/tasks'
export MODE=lite
export GITHUB_WORKSPACE="."

<!-- install hurl -->
INSTALL_DIR=/tmp
VERSION=6.1.1
curl --silent --location https://github.com/Orange-OpenSource/hurl/releases/download/$VERSION/hurl-$VERSION-aarch64-unknown-linux-gnu.tar.gz | tar xvz -C $INSTALL_DIR
export PATH=$INSTALL_DIR/hurl-$VERSION-aarch64-unknown-linux-gnu/bin:$PATH

docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)
pip install . && python3.11 run.py


export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
pyenv global 3.11