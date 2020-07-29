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
    return_code, stdout, stderr = _run_cargo_bench("after")
    # Even if it is the first time this test is run, the benchmark tests should pass.
    # For this purpose, we need to explicitly check the return code.
    assert return_code == 0, "stdout: {}\n stderr: {}".format(stdout, stderr)

    # Move to upstream tip.
    subprocess.run(
        "git fetch {} {}".format(REMOTE, BRANCH),
        shell=True, check=True
    )
    subprocess.run(
        "git checkout {}/{}".format(REMOTE, BRANCH),
        shell=True, check=True
    )

    # Get numbers from upstream tip, without the changes from the current PR.
    return_code, stdout, stderr = _run_cargo_bench("before")
    if return_code == 0:
        # In case this benchmark also ran successfully, we can call critcmp and compare the results.
        _run_critcmp()
    else:
        # The benchmark did not run successfully, but it might be that it is because a benchmark does not exist.
        # In this case, we do not want to fail the test.
        if "error: no bench target named `main`" in stderr:
            # This is a bit of a &*%^ way of checking if the benchmark does not exist.
            # Hopefully it will be possible to check it in another way...soon
            print("There are no benchmarks in master. No comparison can happen.")
        else:
            assert return_code == 0, "stdout: {}\n stderr: {}".format(stdout, stderr)


def _run_cargo_bench(baseline):
    """Runs `cargo bench` and tags the baseline."""
    process = subprocess.run(
        "cargo bench --bench main --all-features -- --noplot --save-baseline {}"
        .format(baseline),
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )

    return process.returncode, process.stdout.decode('utf-8'), process.stderr.decode('utf-8')


def _run_critcmp():
    p = subprocess.run(
        "critcmp before after",
        shell=True, check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print(p.stdout.decode('utf-8'))
    print('ERRORS')
    print(p.stderr.decode('utf-8'))