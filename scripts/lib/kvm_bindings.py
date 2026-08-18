# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import re
import os
import subprocess
from pathlib import Path
from lib.kernel_source import prepare_source
from lib import SUPPORT_ARCHS


KVM_BINDINGS_DIR = "kvm-bindings/src/"


def generate_kvm_bindings(args):
    installed_header_path = prepare_source(args)

    # If arch is not provided, install headers for all supported archs
    if args.arch is None:
        for arch in SUPPORT_ARCHS:
            generate_bindings(
                installed_header_path, arch, args.attribute, args.output_path
            )
    else:
        generate_bindings(
            installed_header_path, args.arch, args.attribute, args.output_path
        )


def generate_bindings(
    installed_header_path: str, arch: str, attribute: str, output_path: str
):
    try:
        # Locate `kvm.h` of specific architecture
        arch_headers = os.path.join(installed_header_path, f"{arch}_headers")
        kvm_header = Path(os.path.join(arch_headers, f"include/linux/kvm.h"))
        if not kvm_header.is_file():
            raise FileNotFoundError(f"KVM header missing at {kvm_header}")

        structs = capture_serde(arch)
        if not structs:
            raise RuntimeError(
                f"No structs found for {arch}, you need to invoke this command under rustvmm/kvm repo root"
            )

        # Build bindgen-cli command with dynamic paths and custom attribute for
        # structures
        base_cmd = [
            "bindgen",
            os.path.abspath(kvm_header),
            "--impl-debug",
            "--impl-partialeq",
            "--with-derive-default",
            "--with-derive-partialeq",
        ]

        for struct in structs:
            base_cmd += ["--with-attribute-custom-struct", f"{struct}={attribute}"]

        # Add include paths relative to source directory
        base_cmd += ["--", f"-I{arch_headers}/include"]  # Use absolute include path

        print(f"\nGenerating bindings for {arch}...")
        bindings = subprocess.run(
            base_cmd, check=True, capture_output=True, text=True, encoding="utf-8"
        ).stdout

        print("Successfully generated bindings")

        output_file_path = f"{output_path}/{arch}/bindings.rs"

        print(f"Generating to: {output_file_path}")

    except subprocess.CalledProcessError as e:
        err_msg = f"Bindgen failed (code {e.returncode})"
        raise RuntimeError(err_msg) from e
    except Exception as e:
        raise RuntimeError(f"Generation failed: {str(e)}") from e

    try:
        with open(output_file_path, "w") as f:
            f.write(bindings)

        # Format with rustfmt
        subprocess.run(["rustfmt", output_file_path], check=True)
        print(f"Generation succeeded: {output_file_path}")
    except subprocess.CalledProcessError:
        raise RuntimeError("rustfmt formatting failed")
    except IOError as e:
        raise RuntimeError(f"File write error: {str(e)}")


def capture_serde(arch: str) -> list[str]:
    """
    Parse serde implementations for specified architecture
    """

    # Locate `serialize.rs` of specific architecture
    target_path = Path(f"{KVM_BINDINGS_DIR}/{arch}/serialize.rs")

    # Validate file existence
    if not target_path.is_file():
        raise FileNotFoundError(
            f"Serialization file not found for {arch}: {target_path}"
        )

    print(f"Extracting serde structs of {arch} from: {target_path}")

    content = target_path.read_text(encoding="utf-8")

    pattern = re.compile(
        r"serde_impls!\s*\{\s*(?P<struct>.*?)\s*\}", re.DOTALL | re.MULTILINE
    )

    # Extract struct list from matched block
    match = pattern.search(content)
    if not match:
        raise ValueError(f"No serde_impls! block found in {target_path}")

    struct_list = match.group("struct")

    structs = []
    for line in struct_list.splitlines():
        for word in line.split():
            clean_word = word.strip().rstrip(",")
            if clean_word:
                structs.append(clean_word)

    return structs
