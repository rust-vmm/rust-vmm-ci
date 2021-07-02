#!/usr/bin/env python3

import json
import os
import platform
import pathlib
import unittest

ROOT_PATH=pathlib.Path(__file__).parent.resolve()

class TestsContainer(unittest.TestCase):
    longMessage = True

def make_test_function(command):
    def test(self):
        os.system(command)
    return test

def retrieve_test_list(config_file=f"{ROOT_PATH}/.buildkite/tests_description.json"):
    with open(config_file) as jsonFile:
        test_list = json.load(jsonFile)
        jsonFile.close()
    return test_list


if __name__ == '__main__':
    test_config = retrieve_test_list()
    for test in test_config["test_list"]:
        command = test["command"]
        command = command.replace("{target_platform}", platform.machine(), 1)
        test_func = make_test_function(command)
        setattr(TestsContainer, 'test_{0}'.format(test["test_name"]), test_func)

    unittest.main()
