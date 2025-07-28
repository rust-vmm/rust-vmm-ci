#!/usr/bin/env python3
#
# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
from pathlib import Path
from lib.kernel_source import prepare_source
from lib.seccompiler import generate_seccompiler, SECCOMPILER_SYSCALL_DIR
from lib.kvm_bindings import generate_kvm_bindings, KVM_BINDINGS_DIR


def main():
    parser = argparse.ArgumentParser(prog="rustvmm_gen")
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser.add_argument("--arch", help="Target architecture (x86_64, arm64, riscv)")
    parser.add_argument("--version", required=True, help="Kernel version (e.g. 6.12.8)")
    parser.add_argument(
        "--install_path",
        default=None,
        help="Header installation directory path",
    )
    parser.add_argument("--keep", help="Keep temporary build files")

    # Prepare subcommand
    prepare_parser = subparsers.add_parser("prepare", help="Prepare kernel headers")
    prepare_parser.set_defaults(func=prepare_source)

    # Generate seccompiler subcommand
    generate_syscall_parser = subparsers.add_parser(
        "generate_seccompiler",
        help="Generate syscall for `rust-vmm/seccompiler` from prepared kernel headers",
    )
    default_seccompiler_syscall_path_prefix = f"{os.getcwd()}/{SECCOMPILER_SYSCALL_DIR}"
    generate_syscall_parser.add_argument(
        "--output_path",
        default=default_seccompiler_syscall_path_prefix,
        help=f"Output directory path (default: {default_seccompiler_syscall_path_prefix})",
    )
    generate_syscall_parser.set_defaults(func=generate_seccompiler)

    # Generate kvm-bindings subcommand
    generate_kvm_bindings_parser = subparsers.add_parser(
        "generate_kvm_bindings",
        help="Generate bindings for `rust-vmm/kvm/kvm-bindings` from prepared kernel headers",
    )
    default_kvm_bindings_path_prefix = f"{os.getcwd()}/{KVM_BINDINGS_DIR}"
    generate_kvm_bindings_parser.add_argument(
        "--output_path",
        default=default_kvm_bindings_path_prefix,
        help=f"Output directory path (default: {default_kvm_bindings_path_prefix})",
    )
    generate_kvm_bindings_parser.add_argument(
        "--attribute",
        help=f"Custom attribute to be added for structures",
    )
    generate_kvm_bindings_parser.set_defaults(func=generate_kvm_bindings)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
