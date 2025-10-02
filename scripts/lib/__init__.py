# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Supported architectures (arch used in kernel)
SUPPORT_ARCHS = ["arm64", "x86_64", "riscv"]

# Map arch used in linux kernel to arch understandable for Rust
MAP_RUST_ARCH = {"arm64": "aarch64", "x86_64": "x86_64", "riscv": "riscv64"}
