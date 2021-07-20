import yaml
import json
import pathlib
import sys
import os

CONTAINER_VERSION = "v12"
DOCKER_PLUGIN_VERSION = "v3.8.0"

X86_AGENT_TAGS = os.getenv('X86_LINUX_AGENT_TAGS')
AARCH64_AGENT_TAGS = os.getenv('AARCH64_LINUX_AGENT_TAGS')
DOCKER_PLUGIN_CONFIG = os.getenv('DOCKER_PLUGIN_CONFIG')

PLATFORMS = ['x86_64.metal', 'arm.metal']
OSS = ['linux']

ROOT_PATH = pathlib.Path(__file__).parent.resolve()


def check_step(step):
    assert step.get('label'),\
        "Label missing."
    assert step.get('commands'),\
        "Commands missing."
    agents = step.get('agents')
    assert agents,\
        "Agents missing."
    assert agents.get('platform') in PLATFORMS,\
        "Invalid or missing platform. The supported platforms are " + \
        ", ".join(PLATFORMS)
    assert agents.get('os') in OSS,\
        "Invalid or missing os. The supported oss are " + \
        ", ".join(OSS)
    assert step.get('plugins'),\
        "Plugins missing."


def override_default_config(step):
    agents = step['agents']
    platform = agents['platform']

    if X86_AGENT_TAGS and platform == 'x86_64.metal':
        agents.clear()
        tags = X86_AGENT_TAGS.split("; ")
        for tag in tags:
            key, val = tag.split(": ")
            agents[key] = val

    if AARCH64_AGENT_TAGS and platform == 'arm.metal':
        agents.clear()
        tags = AARCH64_AGENT_TAGS.split("; ")
        for tag in tags:
            key, val = tag.split(": ")
            agents[key] = val

    if DOCKER_PLUGIN_CONFIG:
        plugins = step['plugins']
        docker = plugins[0][f"docker#{DOCKER_PLUGIN_VERSION}"]
        tags = DOCKER_PLUGIN_CONFIG.split("; ")
        for tag in tags:
            key, val = tag.split(": ")
            val = json.loads(val)
            docker[key] = val


def set_versions(step):
    plugins = step['plugins']
    plugin = plugins[0]
    docker = plugin['docker#{DOCKER_PLUGIN_VERSION}']
    del plugin['docker#{DOCKER_PLUGIN_VERSION}']
    plugin[f"docker#{DOCKER_PLUGIN_VERSION}"] = docker
    docker['image'] = docker['image'].replace(
        "{CONTAINER_VERSION}", CONTAINER_VERSION)


def customize_cfg(json_cfg):
    steps = json_cfg.get('steps')
    assert steps, "Steps missing."

    for step in steps:
        check_step(step)
        set_versions(step)
        override_default_config(step)


def generate_test_pipeline(json_cfg_file=f"{ROOT_PATH}/config.json"):
    with open(json_cfg_file) as json_file:
        json_cfg = json.load(json_file)
        json_file.close()

    customize_cfg(json_cfg)
    yaml.dump(json_cfg, sys.stdout, sort_keys=False)


if __name__ == '__main__':
    generate_test_pipeline()
