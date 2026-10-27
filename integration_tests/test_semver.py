import subprocess

def test_semver():
    """
    Checks crates meet semver
    """

    subprocess.run("cargo install cargo-semver-checks")
    subprocess.run("cargo semver-checks", check=True)