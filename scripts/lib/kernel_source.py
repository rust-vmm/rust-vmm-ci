# Copyright 2025 © Institute of Software, CAS. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import re
import tarfile
import requests
import subprocess
import tempfile
from lib import SUPPORT_ARCHS

KERNEL_ORG_CDN = "https://cdn.kernel.org/pub/linux/kernel"


def prepare_source(args):
    check_kernel_version(args.version)

    # Create `temp_dir` under `/tmp`
    temp_dir = create_temp_dir(args.version)

    # Download kernel tarball from https://cdn.kernel.org/
    tarball = download_kernel(args.version, temp_dir)

    # Extract kernel source
    src_dir = extract_kernel(tarball, temp_dir)

    # If arch is not provided, install headers for all supported archs
    if args.arch is None:
        for arch in SUPPORT_ARCHS:
            installed_header_path = install_headers(
                src_dir=src_dir,
                arch=arch,
                install_path=args.install_path,
            )
    else:
        installed_header_path = install_headers(
            src_dir=src_dir,
            arch=args.arch,
            install_path=args.install_path,
        )

    print(f"\nSuccessfully installed kernel headers to {installed_header_path}")
    return installed_header_path


def check_kernel_version(version):
    """
    Validate if the input kernel version exists in remote. Supports both X.Y
    (namely X.Y.0 and .0 should be omitted) and X.Y.Z formats
    """
    # Validate version format
    if not re.match(r"^\d+\.\d+(\.\d+)?$", version):
        raise ValueError("Invalid version format. Use X.Y or X.Y.Z")

    main_ver = version.split(".")[0]
    base_url = f"{KERNEL_ORG_CDN}/v{main_ver}.x/"
    tarball = f"linux-{version}.tar.xz"

    try:
        # Fetch content of `base_url`
        response = requests.get(base_url, timeout=15)
        response.raise_for_status()

        # Check for exact filename match
        if tarball in response.text:
            print(f"Kernel version {version} found in remote")
            return

        raise RuntimeError(f"Kernel version {version} not found in remote")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise RuntimeError(f"Kernel series v{main_ver}.x does not exist")

        raise RuntimeError(f"HTTP error ({e.response.status_code}): {str(e)}")
    except requests.exceptions.Timeout:
        raise RuntimeError("Connection timeout while checking version")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error: {str(e)}")


def create_temp_dir(version):
    prefix = f"linux-{version}-source-"
    try:
        temp_dir = tempfile.TemporaryDirectory(prefix=prefix, dir="/tmp", delete=False)
        return temp_dir.name
    except OSError as e:
        raise RuntimeError(f"Failed to create temp directory: {e}") from e


def download_kernel(version, temp_dir):
    version_major = re.match(r"^(\d+)\.\d+(\.\d+)?$", version).group(1)
    url = f"{KERNEL_ORG_CDN}/v{version_major}.x/linux-{version}.tar.xz"
    tarball_path = os.path.join(temp_dir, f"linux-{version}.tar.xz")
    print(f"Downloading {url} to {tarball_path}")

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(tarball_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = downloaded / total_size * 100
                        print(f"\rDownloading: {progress:.1f}%", end="")
                print()
        return tarball_path
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e


def extract_kernel(tarball_path, temp_dir):
    print("Extracting...")
    try:
        with tarfile.open(tarball_path, "r:xz") as tar:
            tar.extractall(path=temp_dir)
            extract_path = os.path.join(
                temp_dir, f"{os.path.basename(tarball_path).split('.tar')[0]}"
            )
            print(f"Extracted to {extract_path}")
            return extract_path
    except (tarfile.TarError, IOError) as e:
        raise RuntimeError(f"Extraction failed: {e}") from e


def install_headers(src_dir, arch, install_path):
    # If install_path is not provided, install to parent directory of src_dir to
    # prevent messing up with extracted kernel source code
    if install_path is None:
        install_path = os.path.dirname(src_dir)

    try:
        os.makedirs(install_path, exist_ok=True)

        abs_install_path = os.path.abspath(
            os.path.join(install_path, f"{arch}_headers")
        )
        print(f"Installing to {abs_install_path}")
        result = subprocess.run(
            [
                "make",
                "-C",
                f"{src_dir}",
                f"ARCH={arch}",
                f"INSTALL_HDR_PATH={abs_install_path}",
                "headers_install",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(result.stdout)
        return install_path

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Header installation failed:\n{e.output}"
            f"Temporary files kept at: {os.path.dirname(src_dir)}"
        )
