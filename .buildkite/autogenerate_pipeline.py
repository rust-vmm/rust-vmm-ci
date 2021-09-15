#!/usr/bin/env python3

# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0 OR BSD-3-Clause
"""
This script is printing the Buildkite pipeline.yml to stdout.
This can also be used as a library to print the steps from a different pipeline
specified as a parameter to the `generate_test_pipeline`.

The pipeline is generated based on the test configuration in
`test_description.json`. The JSON file contains a list of tests to be run by
all rust-vmm components.

Some components need to override the default configuration such that they can
access devices while running the tests (for example access to `/dev/kvm`),
access to a temporary volume, and others. Some components may also need to skip
some of the tests. As such, this script supports overriding the following
configurations through environment variables:
- `X86_LINUX_AGENT_TAGS`: overrides the tags by which the x86_64 linux agent is
  selected.
- `AARCH64_LINUX_AGENT_TAGS`: overrides the tags by which the aarch64 linux
  agent is selected.
- `DOCKER_PLUGIN_CONFIG`: specifies additional configuration for the docker
  plugin. For available configuration, please check the
  https://github.com/buildkite-plugins/docker-buildkite-plugin.
- `TESTS_TO_SKIP`: specifies a list of tests to be skipped.
- `TIMEOUTS_MIN`: overrides the timeout value for specific tests.

NOTE: The variable `TESTS_TO_SKIP` is specified as a JSON list with the names
of the tests to be skipped. The variable `TIMEOUTS_MIN` is a dictionary where
each key is the name of a test and each value is the number of minutes for the
timeout. The other variables are specified as dictionaries, where the first key
is `tests` and its value is a list of test names where the configuration should
be applied; the second key is `cfg` and its value is a dictionary with the
actual configuration.

Examples of a valid configuration:
```shell
TESTS_TO_SKIP='["commit-format"]'
DOCKER_PLUGIN_CONFIG='{
    "tests": ["coverage"],
    "cfg": {
        "devices": [ "/dev/vhost-vdpa-0" ],
        "privileged": true
    }
}'
TIMEOUTS_MIN='["style": 30]'
```
"""

import yaml
import json
import os
import sys
import pathlib
import copy

from argparse import ArgumentParser, RawTextHelpFormatter
from textwrap import dedent

# This represents the version of the rust-vmm-container used
# for running the tests.
CONTAINER_VERSION = "v12"
# This represents the version of the Buildkite Docker plugin.
DOCKER_PLUGIN_VERSION = "v3.8.0"

X86_AGENT_TAGS = os.getenv('X86_LINUX_AGENT_TAGS')
AARCH64_AGENT_TAGS = os.getenv('AARCH64_LINUX_AGENT_TAGS')
DOCKER_PLUGIN_CONFIG = os.getenv('DOCKER_PLUGIN_CONFIG')
TESTS_TO_SKIP = os.getenv('TESTS_TO_SKIP')
TIMEOUTS_MIN = os.getenv('TIMEOUTS_MIN')

PARENT_DIR = pathlib.Path(__file__).parent.resolve()


class BuildkiteStep:
    """
    This builds a Buildkite step according to a json configuration and the
    environment variables `X86_LINUX_AGENT_TAGS`, `AARCH64_LINUX_AGENT_TAGS`,
    `DOCKER_PLUGIN_CONFIG`, `TESTS_TO_SKIP` and `TIMEOUTS_MIN`.
    The output is a dictionary.
    """

    def __init__(self):
        """
        Initialize a Buildkite step with default values.
        """

        # Default values.
        # The order in which the attributes are initialized is the same as the
        # order in which the keys will appear in the YAML file, because Python
        # dictionaries are ordered. For readability reasons, this order should
        # not be changed.
        self.label = None
        self.command = None
        self.retry = {'automatic': False}
        self.agents = {'os': 'linux'}
        self.plugins = [
            {
                f"docker#{DOCKER_PLUGIN_VERSION}": {
                    'image': f"rustvmm/dev:{CONTAINER_VERSION}",
                    'always-pull': True
                }
            }
        ]
        self.timeout_in_minutes = 5

    def _set_platform(self, platform):
        """ Set platform if given in the json input. """

        if platform:
            # We need to change `aarch64` to `arm` because of the way we are
            # setting the tags on the host.
            if platform == 'aarch64':
                platform = 'arm'
            self.agents['platform'] = f"{platform}.metal"

    def _set_conditional(self, conditional):
        """ Set conditional if given in the json input. """

        if conditional:
            setattr(self, 'if', conditional)

    def _add_docker_config(self, cfg):
        """ Add configuration for docker if given in the json input. """

        if cfg:
            target = self.plugins[0][f"docker#{DOCKER_PLUGIN_VERSION}"]
            for key, val in cfg.items():
                target[key] = val

    def _env_change_config(self, test_name, env_var, target, override=False):
        """
        Helper function to add to/override configuration of `target`
        if `env_var` is set and this test appears in its list.
        """

        if env_var:
            env_cfg = json.loads(env_var)

            tests = env_cfg.get('tests')
            assert tests,\
                f"Environment variable {env_var} is missing the `tests` key."

            cfg = env_cfg.get('cfg')
            assert cfg,\
                f"Environment variable {env_var} is missing the `cfg` key."

            if test_name in tests:
                if override:
                    target.clear()
                for key, val in cfg.items():
                    target[key] = val

    def _env_override_agent_tags(self, test_name):
        """
        Override the tags by which the linux agent is selected
        using the `X86_LINUX_AGENT_TAGS` and `AARCH64_LINUX_AGENT_TAGS`
        environment variables.
        """

        env_var = None
        platform = self.agents.get('platform')

        # Since the platform is optional, only override the config if the
        # platform was provided.
        if platform:
            if platform == 'x86_64.metal' and X86_AGENT_TAGS:
                env_var = X86_AGENT_TAGS
            if platform == 'arm.metal' and AARCH64_AGENT_TAGS:
                env_var = AARCH64_AGENT_TAGS

        target = self.agents
        self._env_change_config(test_name, env_var, target, override=True)

    def _env_add_docker_config(self, test_name):
        """
        Specify additional configuration for the docker plugin using the
        `DOCKER_PLUGIN_CONFIG` environment variable.
        """

        target = self.plugins[0][f"docker#{DOCKER_PLUGIN_VERSION}"]
        self._env_change_config(test_name, DOCKER_PLUGIN_CONFIG, target)

    def _env_override_timeout(self, test_name):
        if TIMEOUTS_MIN:
            timeouts_min = json.loads(TIMEOUTS_MIN)
            if test_name in timeouts_min:
                self.timeout_in_minutes = timeouts_min[test_name]

    def build(self, input):
        """
        Build a Buildkite step using the `input` configuration that must
        specify some mandatory keys and can also provide optional ones.
        Further configuration from environment variables may be added.
        """

        test_name = input.get('test_name')
        command = input.get('command')
        platform = input.get('platform')
        docker = input.get('docker_plugin')
        conditional = input.get('conditional')

        # Mandatory keys.
        assert test_name, "Step is missing test name."
        platform_string = f"-{platform}" if platform else ""
        self.label = f"{test_name}{platform_string}"

        assert command, "Step is missing command."
        if "{target_platform}" in command:
            assert platform,\
                "Command requires platform, but platform is missing."
            command = command.replace(
                "{target_platform}", platform
            )
        self.command = command

        # Optional keys.
        self._set_platform(platform)
        self._set_conditional(conditional)
        self._add_docker_config(docker)

        # Override/add configuration from environment variables.
        self._env_override_agent_tags(test_name)
        self._env_add_docker_config(test_name)
        self._env_override_timeout(test_name)

        # Return the object's attributes and their values as a dictionary.
        return vars(self)


class BuildkiteConfig:
    """
    This builds the final Buildkite configuration from the json input
    using BuidkiteStep objects. The output is a dictionary that can
    be put into yaml format by the pyyaml package.
    """

    def build(self, input):
        """ Build the final Buildkite configuration fron the json input. """

        self.steps = []
        tests = input.get('tests')
        assert tests, "Input is missing list of tests."

        for test in tests:
            platforms = test.get('platform')
            test_name = test.get('test_name')

            if TESTS_TO_SKIP:
                tests_to_skip = json.loads(TESTS_TO_SKIP)
                if test_name in tests_to_skip:
                    continue

            # The platform is optional. When it is not specified, we don't add
            # it to the step so that we can run the test in any environment.
            if not platforms:
                platforms = [None]

            for platform in platforms:
                step_input = copy.deepcopy(test)
                step_input['platform'] = platform

                step = BuildkiteStep()
                step_output = step.build(step_input)
                self.steps.append(step_output)

        # Return the object's attributes and their values as a dictionary.
        return vars(self)


def generate_pipeline(config_file):
    """ Generate the pipeline yaml file from a json configuration file. """

    with open(config_file) as json_file:
        json_cfg = json.load(json_file)
        json_file.close()

    config = BuildkiteConfig()
    output = config.build(json_cfg)
    yaml.dump(output, sys.stdout, sort_keys=False)


if __name__ == '__main__':
    help_text = dedent(
        """
        This script supports overriding the following configurations through
        environment variables:
        - X86_LINUX_AGENT_TAGS: overrides the tags by which the x86_64 linux
        agent is selected.
        - AARCH64_LINUX_AGENT_TAGS: overrides the tags by which the aarch64
        linux agent is selected.
        - DOCKER_PLUGIN_CONFIG: specifies additional configuration for the
        docker plugin. For available configuration, please check
        https://github.com/buildkite-plugins/docker-buildkite-plugin.
        - TESTS_TO_SKIP: specifies a list of tests to be skipped.
        - TIMEOUTS_MIN: overrides the timeout value for specific tests.
        """
    )
    parser = ArgumentParser(description=help_text,
                            formatter_class=RawTextHelpFormatter)
    # By default we're generating the rust-vmm-ci pipeline with the test
    # configuration committed to this repository.
    # This parameter is useful for generating the pipeline for repositories
    # that have custom pipelines, and it helps with keeping the container
    # version the same across pipelines.
    parser.add_argument('-t', '--test-description',
                        metavar="JSON_FILE",
                        help='The path to the JSON file containing the test'
                             ' description for the CI.',
                        default=f'{PARENT_DIR}/test_description.json')
    args = parser.parse_args()
    generate_pipeline(args.test_description)
