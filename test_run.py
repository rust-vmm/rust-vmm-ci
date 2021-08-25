#!/usr/bin/env python3

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR BSD-3-Clause
import json
import subprocess
import platform
import pathlib
import unittest

PARENT_DIR = pathlib.Path(__file__).parent.resolve()


class TestsContainer(unittest.TestCase):
    pass


def make_test_function(command):
    def test(self):
        subprocess.run(command, shell=True, check=True)
    return test


def retrieve_test_list(
    config_file=f"{PARENT_DIR}/.buildkite/test_description.json"
):
    with open(config_file) as jsonFile:
        test_list = json.load(jsonFile)
        jsonFile.close()
    return test_list


if __name__ == '__main__':
    test_config = retrieve_test_list()
    for test in test_config['tests']:
        command = test['command']
        command = command.replace("{target_platform}", platform.machine())
        test_func = make_test_function(command)
        setattr(TestsContainer, 'test_{}'.format(test['test_name']), test_func)

    unittest.main(verbosity=2)
