import logging
import argparse
import os
import sys
import time
import glob
from socket import gethostname

from containerized_test_runner import Runner, ExecutionTestResults, SuiteLoader, ScenarioLoader, ExecutionTestSucceeded, ExecutionTestFailed
from .docker import DockerDriver
from .docker_webapp import DockerWebAppDriver

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
    parser.add_argument("--driver", help="driver", default="DockerDriver")
    parser.add_argument("--hurl-image", help="hurl image with tag", default="ghcr.io/orange-opensource/hurl:latest")
    parser.add_argument("--scenario-dir", help="directory containing MC scenario Python files")
    parser.add_argument("--task-root", dest="task_root", help="path to task directory to mount into container")
    parser.add_argument("suites", nargs='*')
    return parser

def does_suite_have_tests(suite_results):
    return len(suite_results.evaluated) > 0

def execute_tests(args):
    if args.driver == "DockerWebAppDriver":
        driver = DockerWebAppDriver(vars(args))
    if args.driver == "DockerDriver":
        driver = DockerDriver(vars(args))

    with Runner(driver=driver, args=args) as app:

        suites = []
        scenarios = []

        # Load traditional test suites
        if args.suites:
            for path in args.suites:
                paths = glob.glob(path, recursive=True)

                if len(paths) == 0:
                    logger.error("No suites found via the path '{}'.".format(path))
                    sys.exit(1)

                logger.debug("Found the suites {} via the path '{}'.".format(paths, path))
                suites.extend(paths)

        # Load MC scenarios if scenario directory is provided
        if args.scenario_dir:
            scenarios = ScenarioLoader.load_scenarios_from_directory(args.scenario_dir)
            logger.info(f"Loaded {len(scenarios)} MC scenarios from {args.scenario_dir}")

        if not suites and not scenarios:
            logger.error("No test suites or scenarios provided.")
            sys.exit(1)

        logger.debug("The list of suites to be ran is {}.".format(suites))
        logger.info("The tests are being ran on host {}".format(gethostname()))

        run_results = []
        exit_unsuccessfully = False

        # Run traditional test suites
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

        # Run MC scenarios
        for scenario in scenarios:
            scenario_results = ExecutionTestResults({"name": scenario.name})
            try:
                results = driver.execute_concurrent(scenario)
                scenario_results.evaluated = [{"name": f"{scenario.name}_req{i}"} for i in range(len(results))]
                
                for result in results:
                    if isinstance(result, ExecutionTestSucceeded):
                        scenario_results.succeeded.append(result)
                    elif isinstance(result, ExecutionTestFailed):
                        scenario_results.failed.append(result)
                        scenario_results.failed_names.append(result.test.get("name", "unknown"))
                        exit_unsuccessfully = True
                
            except Exception as e:
                logger.error(f"Failed to execute scenario {scenario.name}: {e}")
                exit_unsuccessfully = True
                scenario_results.failed.append(ExecutionTestFailed(
                    {"name": scenario.name}, 
                    ExecutionTestFailed.UNKNOWN_ERROR, 
                    str(e)
                ))
                scenario_results.failed_names.append(scenario.name)

            run_results.append((scenario.name, scenario_results))
    
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
