import logging
import argparse
import os
import sys
import time
import glob
from socket import gethostname

from containerized_test_runner import Runner, ExecutionTestResults, SuiteLoader
from .docker import DockerDriver

logger = logging.getLogger("test-harness")

class Module:
    def __init__(self, name):
        self.name = name
        self.__name__ = name


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super(ArgumentParser, self).__init__()

def ensure_directory_exists(target_file):
    if os.path.exists(os.path.dirname(target_file)):
        return
    os.makedirs(os.path.dirname(target_file))

def write_test_summary(run_results):

    totals = {
        "evaluated": 0,
        "succeeded": 0,
        "skipped": 0,
        "failed": 0,
        "failed_names": [],
        "empty_suites": [],
    }

    for (suite_name, suite_results) in run_results:
        totals["evaluated"] += len(suite_results.evaluated)
        totals["succeeded"] += len(suite_results.succeeded)
        totals["skipped"] += len(suite_results.skipped)
        totals["failed"] += len(suite_results.failed)
        totals["failed_names"] += [f'{suite_name}/{n}' for n in suite_results.failed_names]

        if not does_suite_have_tests(suite_results):
            totals["empty_suites"].append(suite_name)

    print("")
    if len(totals["failed_names"]) > 0:
        print("Failed Tests")
        print("-----")
        print("\n".join(totals["failed_names"]))

    if len(totals["empty_suites"]) > 0:
        print("Empty Suites")
        print("-----")
        print(*totals["empty_suites"], sep = "\n")

    print("-----")

    for (suite_name, suite_results) in run_results:
        print("{}: {} passed, {} failed, {} errors, {} skipped".format(
            suite_name,
            len(suite_results.succeeded),
            len(suite_results.failed),
            0,
            len(suite_results.skipped),
        ))

    print("TOTAL: {} passed, {} failed, {} errors, {} skipped".format(
        totals["succeeded"],
        totals["failed"],
        0,
        totals["skipped"],
    ))


def create_parser():
    parser = ArgumentParser()
    parser.add_argument("--debug", dest="debug", action="store_true")
    parser.add_argument("--test-image", help="docker image to test")
    parser.add_argument("--task-root", default="/int-tests", help="location of task resources")
    parser.add_argument("suites", nargs='+')
    return parser


def does_suite_have_tests(suite_results):
    return len(suite_results.evaluated) > 0

def execute_tests(args):
    with Runner(driver=DockerDriver(vars(args)), args=args) as app:

        suites = []

        for path in args.suites:
            paths = glob.glob(path, recursive=True)

            if len(paths) == 0:
                logger.error("No suites found via the path '{}'.".format(path))
                sys.exit(1)

            logger.debug("Found the suites {} via the path '{}'.".format(paths, path))
            suites.extend(paths)

        logger.debug("The list of suites to be ran is {}.".format(suites))
        logger.info("The tests are being ran on host {}".format(gethostname()))

        run_results = []
        exit_unsuccessfully = False

        for suite_file in suites:
            suite = app.load_suite_from_file(suite_file)
            suite_results = ExecutionTestResults({"name": suite["name"]})
            app.run_suite(suite, [], suite_results)
            if len(suite_results.failed) > 0:
                exit_unsuccessfully = True

            if not does_suite_have_tests(suite_results):
                logger.error("The suite '{}' has no tests configured.".format(suite["name"]))
                exit_unsuccessfully = True

            run_results.append((suite["name"], suite_results))
    
        write_test_summary(run_results)

        if exit_unsuccessfully:
            sys.exit(1)

        sys.exit(0)

def main():

    parser = create_parser()

    args = parser.parse_args()

    logging.Formatter.converter = time.gmtime
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S.%Z')
    execute_tests(args)

if __name__ == "__main__":
    main()
