import copy
import json
import logging


class SuiteLoader:
    """
    Common routines for handling test suites
    """

    logger = logging.getLogger("Runner")

    @classmethod
    def load_suite_from_file(cls, src):
        cls.logger.debug("loading suite %s", src)
        with open(src, "r", encoding="utf-8") as file:
            suite = json.loads(file.read())
            suite["name"] = cls._get_suite_name(src)
            return suite

    @classmethod
    def generate_tests(cls, suite):
        """Generator that produces the complete set of rendered tests for a suite"""

        tests = suite["tests"]
        test_defaults = suite.get("default", {})

        if "template" in suite:
            tests = cls.expand_template(suite["template"], tests)

        for t in tests:
            cls.apply_defaults(t, test_defaults)
            yield t

    @classmethod
    def expand_template(cls, template, tests):
        """Expand a set of tests with the provided template dictionary"""
        res = []
        for t in tests:
            # If the test specifics a template key, then we do not template it
            template_keys = [k for k in sorted(template.keys()) if k not in t]
            for suffix, expand in cls._generate_template_expansion(
                template, template_keys, {}
            ):
                xt = copy.copy(t)
                cls.logger.debug("Expand %s with %s", xt["name"], suffix)
                xt["name"] += ":" + suffix
                cls.apply_defaults(xt, expand)
                res.append(xt)
        return res

    @classmethod
    def _get_suite_name(cls, suite_path):
        # Create the name from the parent directory
        return "/".join(suite_path.split("/")[-2:])

    @classmethod
    def _generate_template_expansion(cls, template, keys, state):
        """Given a set of template expansions, recursively generate all permutations"""
        k = keys[0]
        for v in template[k]:
            state = copy.copy(state)
            state[k] = v
            if len(keys) == 1:
                yield str(v), state
            else:
                for suffix, substate in cls._generate_template_expansion(
                    template, keys[1:], state
                ):
                    yield (str(v) + ":" + suffix), substate

    @classmethod
    def apply_defaults(cls, content, defaults):
        """Provide defaults for any key that is not set in content"""
        for k in defaults:
            content[k] = content.get(k, defaults[k])

    @staticmethod
    def add_testsuite_prefix(suite, prefix):
        if "name" in suite:
            parts = suite["name"].split("/")
            suite["name"] = "{}/{}.{}".format(parts[0], prefix, parts[-1])
        return suite
