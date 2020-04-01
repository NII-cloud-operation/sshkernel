import os
import subprocess


def _run(cmd):
    print("run: {}".format(cmd))

    return subprocess.check_output(
        cmd, shell=True, encoding="utf-8", universal_newlines=True
    )


def make_ssh_config(host, keyfile):

    _run("chmod 600 {keyfile}".format(keyfile=keyfile))
    _run("mkdir -p ~/.ssh; chmod 700 ~/.ssh")
    target = os.path.expanduser("~/.ssh/config")
    config = """
Host {host}
    Hostname {hostname}
    User root
    Port 22
    IdentityFile {keyfile}
""".format(
        host=host, hostname=host, keyfile=keyfile
    )

    with open(target, "a") as f:
        f.write(config)

    print("wrote {target}".format(target=target))


def setup_remotecommand(keyfile):
    """Setup proxycommand config.
    terminal -- bastion -- target
    * terminal is the main container (py37)
    * bastion is root@ubuntu
    * target is root@localhost

    bastion and target is the same container
    because GitLab CI doesn't support inter-service name resolution currently.

    * add ssh_config entry in terminal with proxycommand
    """
    config = """
# target from bastion
Host {target}
    User root
    Port 22
    IdentityFile {keyfile}
    ProxyCommand ssh -W %h:%p {bastion}
""".format(
        target="localhost", bastion="ubuntu18", keyfile=keyfile,
    )
    with open(os.path.expanduser("~/.ssh/config"), "a") as f:
        f.write(config)

    print("wrote proxycommand config")

    print(_run("ssh ubuntu18 \"ssh-keygen -f ~/.ssh/id_rsa -N ''\""))
    print(_run('ssh ubuntu18 "ssh-keyscan -H localhost >> ~/.ssh/known_hosts"'))
    print(_run("ssh ubuntu18 -- 'apt-get update && apt-get install -y sshpass'"))
    print(_run("ssh ubuntu18 -- sshpass -p root ssh-copy-id localhost"))

    print(_run("ssh ubuntu18 'env |grep SSH'"))
    print(_run("ssh ubuntu18 'ssh localhost \"env |grep SSH\"'"))


def update_known_hosts(host):
    cmd = "ssh-keyscan -H {host} >> ~/.ssh/known_hosts".format(host=host)
    buf = _run(cmd)
    print(buf)


def install_sshpass():
    cmd = "apt-get update && apt-get install -yq sshpass"
    print(_run(cmd))


def ssh_copy_id(host, key, password):
    cmd = "sshpass -p {password} ssh-copy-id -i {key} {host}".format(
        key=key, host=host, password=password
    )
    print(_run(cmd))


def check_login(host):
    print(_run("cat ~/.ssh/config"))

    cmd = "ssh {host} echo ok".format(host=host)
    buf = _run(cmd)

    assert "ok" in buf


def install_sshkernel():
    cmd = "python -msshkernel install"
    print(_run(cmd))


def main():
    hosts = [
        ("ubuntu18", "root", "root"),
        ("centos7", "root", "indig0!"),
    ]

    for (host, _user, password) in hosts:
        base = os.path.dirname(__file__)
        keyfile = os.path.abspath("{base}/id_rsa".format(base=base))

        if host.startswith("ubuntu"):
            install_sshpass()

        make_ssh_config(host, keyfile)
        update_known_hosts(host)
        ssh_copy_id(host, keyfile, password)

        check_login(host)

    setup_remotecommand(keyfile)
    install_sshkernel()


main()
