from subprocess import Popen, PIPE, STDOUT


def test_cargo_audit():
    cmd = 'cargo-audit audit'
    prs = Popen("{}".format(cmd), shell=True, stdin=PIPE,
            stdout=PIPE, stderr=STDOUT, close_fds=True)
    stdout, nothing = prs.communicate()
    print(stdout)

