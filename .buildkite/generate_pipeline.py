#!/usr/bin/env python3

"""
This script is printing the Buildkite pipeline.yml to stdout.
This can also be used as a library to print the steps from a different pipeline
specified as a parameter to the `generate_test_pipeline`.

The pipeline is generated based on the test configuration in
`test_description.json`. The JSON contains list of tests to be run by all
rust-vmm components.

Some components need to override the default configuration such that they can
access devices while running the tests (for example access to `/dev/kvm`),
access to a temporary volume, and others. As such, this script supports
overriding the following configurations through environment variables:
- `X86_LINUX_AGENT_TAGS`: overrides the tags by which the x86_64 linux agent is
  selected. The default tags are `platform: x86_64.metal, os: linux`.
- `AARCH64_LINUX_AGENT_TAGS`: overrides the tags by which the aarch64 linux
  agent is selected.
- `DOCKER_PLUGIN_CONFIG`: specifies additional configuration for the docker
  plugin. For available configuration, please check the
  https://github.com/buildkite-plugins/docker-buildkite-plugin. For now this
  support is limited to key value pairs. Examples of valid plugin
  configurations:
  DOCKER_PLUGIN_CONFIG="devices: [ "/dev/vhost-vdpa-0" ], privileged: true"

NOTE: The environment variables are specified as key value pairs, where the key
is separated by the value through a colon followed by a space (`: `), and the
pairs are separated by a comma followed by a space (`, `).
"""

import json
import os
import pathlib

CONTAINER_VERSION="v12"
DOCKER_PLUGIN_VERSION="v3.8.0"

ROOT_PATH=pathlib.Path(__file__).parent.resolve()
# The following default can be overwritten through the `X86_LINUX_AGENT_TAGS` env variable.
DEFAULT_X86_LINUX_AGENT_TAGS="platform: x86_64.metal, os: linux"
# The following default can be overwritten through the `AARCH64_LINUX_AGENT_TAGS` env variable.
DEFAULT_AARCH64_LINUX_AGENT_TAGS="platform: arm.metal, os: linux"


def retrieve_test_list(config_file):
    with open(config_file) as jsonFile:
        test_list = json.load(jsonFile)
        jsonFile.close()
    return test_list


def get_platform_tags(platform):
    if platform == "x86_64":
        return os.getenv('X86_LINUX_AGENT_TAGS', DEFAULT_X86_LINUX_AGENT_TAGS)
    elif platform == "aarch64":
        return os.getenv('AARCH64_LINUX_AGENT_TAGS', DEFAULT_AARCH64_LINUX_AGENT_TAGS)


def print_agent_tags(platform):
    agent_tags = get_platform_tags(platform)
    tags = agent_tags.split(", ")
    for tag in tags:
        print(f"      {tag}")


def print_docker_plugin_config(json_docker_config):
    for key, value in json_docker_config.items():
        # In yaml the booleans are lower case (true, false), while in Python
        # they're upper case (True, False). The following line is a hack
        # to convert it to lower case.
        if type(value) == bool:
            value = str(value).lower()
        print(f"          {key}: {value}")

    # Check if there is any user defined docker config as well.
    docker_plugin_config_list = os.getenv('DOCKER_PLUGIN_CONFIG', "").split(", ")
    for docker_plugin_config in docker_plugin_config_list:
        print(f"          {docker_plugin_config}")


def generate_test_pipeline(config_file=f"{ROOT_PATH}/tests_description.json"):
    test_list = retrieve_test_list(config_file)

    # TODO: implement this with a class that knows about the needed indent so
    # we don't need to count how many spaces are needed....
    print("steps:")

    for test in test_list["test_list"]:
        for platform in test["platform"]:
            label = "{}-{}".format(test['test_name'], platform)
            command = test['command'].replace("{target_platform}", platform)
            conditional = test.get("conditional", "")
            buildkite_conditional = f"    if: {conditional}\n" if conditional else ""
            print(
                f"  - label: \"{label}\"\n"
                "    commands:\n"
                f"     - {command}\n"
                f"{buildkite_conditional}"
                "    retry:\n"
                "      automatic: false\n"
                "    agents:")
            print_agent_tags(platform),
            print(
                "    plugins:\n"
                f"      - docker#{DOCKER_PLUGIN_VERSION}:\n"
                f"          image: \"rustvmm/dev:{CONTAINER_VERSION}\"\n"
                "          always-pull: true"
            )
            print_docker_plugin_config(test.get("docker_plugin", {}))
            print("\n")


if __name__ == '__main__':
    generate_test_pipeline()
