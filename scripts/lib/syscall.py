# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import subprocess
import re


def generate_syscall_table(file_path):
    """Generate syscall table from specified header file"""
    try:
        with open(file_path, "r") as f:
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

    except FileNotFoundError:
        raise RuntimeError(f"Header file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"File processing failed: {str(e)}")


def generate_rust_code(syscalls, output_path):
    """Generate Rust code and format with rustfmt"""
    print(f"Generating to: {output_path}")
    code = f"""use std::collections::HashMap;
pub(crate) fn make_syscall_table() -> HashMap<&'static str, i64> {{
    vec![
        {syscalls}
    ].into_iter().collect()
}}
"""
    try:
        with open(output_path, "w") as f:
            f.write(code)

        # Format with rustfmt
        subprocess.run(["rustfmt", output_path], check=True)
        print(f"Generation succeeded: {output_path}")
    except subprocess.CalledProcessError:
        raise RuntimeError("rustfmt formatting failed")
    except IOError as e:
        raise RuntimeError(f"File write error: {str(e)}")
