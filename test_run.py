#!/usr/bin/env python3

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR BSD-3-Clause
import json
import subprocess
import platform
import pathlib
import unittest

from argparse import ArgumentParser, RawTextHelpFormatter
from textwrap import dedent

PARENT_DIR = pathlib.Path(__file__).parent.resolve()


class TestsContainer(unittest.TestCase):
    pass


def make_test_function(command):
    def test(self):
        subprocess.run(command, shell=True, check=True)

    return test


def retrieve_test_list(config_file=f"{PARENT_DIR}/.buildkite/test_description.json"):
    with open(config_file) as jsonFile:
        test_list = json.load(jsonFile)
        jsonFile.close()
    return test_list


if __name__ == "__main__":
    help_text = dedent(
        """
        This script allows running all the tests at once on the local machine.
        The tests "test_benchmark.py" and "test_commit_format.py" work properly
        on the local machine only when the environment variables REMOTE and
        BASE_BRANCH are set. Otherwise the default values are "origin" for the
        remote name of the upstream repository and "main" for the name of the
        base branch, and these tests may not work as expected.
        """
    )
    parser = ArgumentParser(description=help_text, formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "-l",
        "--list-tests",
        action="store_true",
        default=False,
        help="List available tests",
    )
    parser.add_argument(
        "tests",
        nargs="*",
        help="The tests to run. If none are specified run all the available tests.",
    )
    args = parser.parse_args()

    test_config = retrieve_test_list()

    for test in test_config["tests"]:
        name = test["test_name"]

        if len(args.tests) > 0:
            if name not in args.tests:
                continue

        command = test["command"]
        command = command.replace("{target_platform}", platform.machine())
        if args.list_tests:
            print(f"{name}: {command}")
        else:
            test_func = make_test_function(command)
            setattr(TestsContainer, f"test_{name}", test_func)

    if not args.list_tests:
        tests_suite = unittest.TestLoader().loadTestsFromTestCase(TestsContainer)
        unittest.TextTestRunner(verbosity=2).run(tests_suite)
