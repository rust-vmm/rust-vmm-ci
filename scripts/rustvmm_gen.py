#!/usr/bin/env python3
#
# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
from pathlib import Path
from lib.kernel_source import (
    check_kernel_version,
    create_temp_dir,
    download_kernel,
    extract_kernel,
    install_headers,
)
from lib.syscall import (
    generate_syscall_table,
    generate_rust_code,
)

# Map arch used in linux kernel to arch understandable for Rust
MAP_RUST_ARCH = {"arm64": "aarch64", "x86_64": "x86_64", "riscv": "riscv64"}


def prepare_command(args):
    check_kernel_version(args.version)

    # Create `temp_dir` under `/tmp`
    temp_dir = create_temp_dir(args.version)

    # Download kernel tarball from https://cdn.kernel.org/
    tarball = download_kernel(args.version, temp_dir)

    # Extract kernel source
    src_dir = extract_kernel(tarball, temp_dir)

    # Get headers of specific architecture
    installed_header_path = install_headers(
        src_dir=src_dir,
        arch=args.arch,
        install_path=args.install_path,
    )

    print(f"\nSuccessfully installed kernel headers to {installed_header_path}")
    return src_dir


def generate_syscall_command(args):
    src_dir = prepare_command(args)

    # Generate syscall table
    header_path = os.path.join(
        os.path.dirname(src_dir), f"{args.arch}_headers/include/asm/unistd_64.h"
    )
    syscalls = generate_syscall_table(header_path)

    # Create output directory if needed
    args.output_path.mkdir(parents=True, exist_ok=True)

    # Generate architecture-specific filename
    output_file_path = args.output_path / f"{MAP_RUST_ARCH[args.arch]}.rs"

    # Generate Rust code
    generate_rust_code(syscalls, output_file_path)


def main():
    parser = argparse.ArgumentParser(prog="rustvmm_gen")
    subparsers = parser.add_subparsers(dest="command", required=True)
    parser.add_argument("--arch", help="Target architecture (x86_64, arm64, riscv64)")
    parser.add_argument("--version", help="Kernel version (e.g. 6.12.8)")
    parser.add_argument(
        "--install_path",
        default=None,
        help="Header installation directory path",
    )
    parser.add_argument("--keep", help="Keep temporary build files")

    # Prepare subcommand
    prepare_parser = subparsers.add_parser("prepare", help="Prepare kernel headers")
    prepare_parser.set_defaults(func=prepare_command)

    # Generate syscall subcommand
    generate_syscall_parser = subparsers.add_parser(
        "generate_syscall",
        help="Generate syscall for `rust-vmm/seccompiler` from prepared kernel headers",
    )
    generate_syscall_parser.add_argument(
        "--output_path",
        type=Path,
        default=os.getcwd(),
        help="Output directory path (default: current)",
    )
    generate_syscall_parser.set_defaults(func=generate_syscall_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
