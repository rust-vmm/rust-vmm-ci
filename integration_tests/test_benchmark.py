# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compare benchmark results before and after a pull request."""

import os, subprocess
import pytest

from utils import get_repo_root_path

# Buildkite clones with the remote name "origin". It's non-configurable.
REMOTE = "origin"
# Possibly prone to changes.
BRANCH = "master"


def test_bench():
    """Runs benchmarks before and after and compares the results."""
    os.chdir(get_repo_root_path())

    # Get numbers for current HEAD.
    _run_cargo_bench("after")

    # Move to upstream tip.
    subprocess.run(
        "git checkout {}/{}".format(REMOTE, BRANCH),
        shell=True, check=True
    )

    # Get numbers from upstream tip, without the changes from the current PR.
    _run_cargo_bench("before")

    # Compare.
    p = subprocess.run(
        "critcmp before after",
        shell=True, check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print(p.stdout.decode('utf-8'))
    print('ERRORS')
    print(p.stderr.decode('utf-8'))


def _run_cargo_bench(baseline):
    """Runs `cargo bench` and tags the baseline."""
    subprocess.run(
        "cargo bench --all-features -- --noplot --save-baseline {}"
        .format(baseline),
        shell=True, check=True
    )
