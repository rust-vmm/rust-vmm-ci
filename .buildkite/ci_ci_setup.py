#!/usr/bin/env python3

from subprocess import run
from textwrap import dedent

if __name__ == '__main__':
    commands = '''
        tar cf archive ./*
        mkdir rust-vmm-ci
        mv archive rust-vmm-ci

        mkdir src
        echo "\\
        pub fn main() {\\n\\
            println!(\\"It works!\\");\\n\\
        }\\
        " > src/lib.rs

        echo "\\
        [package]\\n\\
        name = \\"rust-vmm-ci\\"\\n\\
        version = \\"0.1.0\\"\\n\\n\\
        [dependencies]\\n\\
        " > Cargo.toml

        echo "\\
        {\\n\\
        \\"coverage_score\\": 33.3,\\n\\
        \\"exclude_path\\": \\"\\",\\n\\
        \\"crate_features\\": \\"\\"\\n\\
        }" | tee -a \\
        coverage_config_x86_64.json coverage_config_aarch64.json \\
        > /dev/null

        cd rust-vmm-ci
        tar xf archive --directory ./
    '''
    commands = dedent(commands)
    run(commands, shell=True)
