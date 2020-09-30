# SPDX-License-Identifier: Apache-2.0
import subprocess 

def test_cargo_audit():
    cmd = 'cargo-audit'
    prs = subprocess.run("{}".format(cmd), shell=True, check=True)
    stdout, nothing = prs.communicate()
