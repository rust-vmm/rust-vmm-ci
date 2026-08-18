# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import subprocess
import os
import re
from lib.kernel_source import prepare_source
from lib import MAP_RUST_ARCH, SUPPORT_ARCHS
from pathlib import Path

SECCOMPILER_SYSCALL_DIR = "src/syscall_table"


def generate_seccompiler(args):
    installed_header_path = prepare_source(args)

    # If arch is not provided, install headers for all supported archs
    if args.arch is None:
        for arch in SUPPORT_ARCHS:
            generate_rust_code(installed_header_path, arch, args.output_path)
    else:
        generate_rust_code(installed_header_path, args.arch, args.output_path)


def generate_rust_code(installed_header_path: str, arch: str, output_path: str):
    # Generate syscall table
    arch_headers = os.path.join(installed_header_path, f"{arch}_headers")
    syscall_header = Path(os.path.join(arch_headers, f"include/asm/unistd_64.h"))
    if not syscall_header.is_file():
        raise FileNotFoundError(f"syscall headers missing at {syscall_header}")
    syscalls = generate_syscall_table(syscall_header)

    arch = MAP_RUST_ARCH[arch]
    output_file_path = f"{output_path}/{arch}.rs"

    """Generate Rust code and format with rustfmt"""
    print(f"Generating to: {output_file_path}")
    code = f"""use std::collections::HashMap;
pub(crate) fn make_syscall_table() -> HashMap<&'static str, i64> {{
    vec![
        {syscalls}
    ].into_iter().collect()
}}
"""
    try:
        with open(output_file_path, "w") as f:
            f.write(code)

        # Format with rustfmt
        subprocess.run(["rustfmt", output_file_path], check=True)
        print(f"Generation succeeded: {output_file_path}")
    except subprocess.CalledProcessError:
        raise RuntimeError("rustfmt formatting failed")
    except IOError as e:
        raise RuntimeError(f"File write error: {str(e)}")


def generate_syscall_table(syscall_header_path: str):
    """Generate syscall table from specified header file"""
    try:
        with open(syscall_header_path, "r") as f:
            syscalls = []
            pattern = re.compile(r"^#define __NR_(\w+)\s+(\d+)")

            for line in f:
                line = line.strip()
                if line.startswith("#define __NR_"):
                    match = pattern.match(line)
                    if match:
                        name = match.group(1)
                        num = int(match.group(2))
                        syscalls.append((name, num))

            # Sort alphabetically by syscall name
            syscalls.sort(key=lambda x: x[0])
            syscall_list = [f'("{name}", {num}),' for name, num in syscalls]
            return " ".join(syscall_list)

    except Exception as e:
        raise RuntimeError(f"File processing failed: {str(e)}")
