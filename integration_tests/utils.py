# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os


def get_repo_root_path():
    """Terrible hack to get the root path of the repository."""
    integration_tests_path = os.path.dirname(os.path.realpath(__file__))
    rust_vmm_ci_path = os.path.dirname(integration_tests_path)

    return os.path.dirname(rust_vmm_ci_path)
