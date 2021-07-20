import yaml
import json
import pathlib
import sys
import os

CONTAINER_VERSION = "v12"
DOCKER_PLUGIN_VERSION = "v3.8.0"

ROOT_PATH = pathlib.Path(__file__).parent.resolve()


def check_format(json_cfg):
    platforms = {'x86_64.metal', 'arm.metal'}
    oss = {'linux'}

    steps = json_cfg.get('steps')
    assert steps,\
        "Steps missing."
    for step in steps:
        assert step.get('label'),\
            "Label missing."
        assert step.get('commands'),\
            "Commands missing."
        agents = step.get('agents')
        assert agents,\
            "Agents missing."
        assert agents.get('platform') in platforms,\
            "Invalid or missing platform."
        assert agents.get('os') in oss,\
            "Invalid or missing os."


def customize_cfg(json_cfg):
    x86_agent_tags = os.getenv('X86_LINUX_AGENT_TAGS')
    aarch64_agent_tags = os.getenv('AARCH64_LINUX_AGENT_TAGS')
    docker_plugin_config = os.getenv('DOCKER_PLUGIN_CONFIG')

    if x86_agent_tags or aarch64_agent_tags or docker_plugin_config:
        steps = json_cfg['steps']
        for step in steps:
            agents = step['agents']
            platform = agents['platform']
            if x86_agent_tags and platform == 'x86_64.metal':
                agents.clear()
                tags = x86_agent_tags.split(", ")
                for tag in tags:
                    key, val = tag.split(": ")
                    agents[key] = val

            if aarch64_agent_tags and platform == 'arm.metal':
                agents.clear()
                tags = aarch64_agent_tags.split(", ")
                for tag in tags:
                    key, val = tag.split(": ")
                    agents[key] = val

            if docker_plugin_config:
                plugins = step['plugins']
                docker = plugins[0][f"docker#{DOCKER_PLUGIN_VERSION}"]
                tags = docker_plugin_config.split(", ")
                for tag in tags:
                    key, val = tag.split(": ")
                    val = json.loads(val)
                    docker[key] = val


def generate_test_pipeline(json_cfg_file=f"{ROOT_PATH}/config.json"):
    with open(json_cfg_file) as json_file:
        json_cfg = json.load(json_file)
        json_file.close()

    check_format(json_cfg)
    customize_cfg(json_cfg)
    yaml.dump(json_cfg, sys.stdout, sort_keys=False)


if __name__ == '__main__':
    generate_test_pipeline()
