# SSH Kernel

SSH Kernel is a Jupyter kernel specialized in executing commands remotely
with [paramiko](http://www.paramiko.org/) SSH client.

![](doc/screenshot.png)

## Major requirements

* Python3.5+
* IPython 7.0+

## Recommended system requirements

Host OS (running notebook server):

* Ubuntu 18.04+
* Windows 10 WSL (Ubuntu 18.04+)

Target OS (running sshd):

* Ubuntu16.04+
* CentOS6+

## Installation

Please adopt installation option depends on your Python environment.

```
pip install -U sshkernel
python -m sshkernel install [--user|--sys-prefix]
# `python -m sshkernel install --help` for more information.
```

Verify that sshkernel is installed correctly by listing available Jupyter kernel specs:

```
$ jupyter kernelspec list
Available kernels:
  python3        /tmp/env/share/jupyter/kernels/python3
  ssh            /tmp/env/share/jupyter/kernels/ssh  # <--

  (Path differs depends on environment)
```

To upgrade:

```
pip install --upgrade sshkernel
```

To uninstall:

```
jupyter kernelspec remove ssh
pip uninstall sshkernel
```

### Notes about python environment

The latest version of this library is mainly developed with Python 3.7.3 installed with `pyenv`.

CI is performed with Python3.6 and 3.7 on [Debian based container without conda](https://hub.docker.com/_/python),
and manual test is performed with Ubuntu based container with conda, which derived from [official Jupyter Notebook stack](https://hub.docker.com/r/jupyter/minimal-notebook/).
`Anaconda` on Windows 10 is also confirmed, but is less tested in our development/production.

## Getting Started

Basic examples of using SSH Kernel:

* [Getting Started](https://github.com/NII-cloud-operation/sshkernel/blob/master/examples/getting-started.ipynb)
* [Getting Started (in Japanese)](https://github.com/NII-cloud-operation/sshkernel/blob/master/examples/getting-started-ja.ipynb)

## Configuration

SSH Kernel obtains configuration data from `~/.ssh/config` file to connect servers.

Possible keywords are as follows:

* HostName
* User
* Port
* IdentityFile
* ForwardAgent

### Notes about private keys

* As private key files in `~/.ssh/` are discoverable, you do not necessarily specify `IdentityFile`
* If you use a ed25519 key, please generate with or convert into old PEM format
    * e.g. `ssh-keygen -m PEM -t ed25519 ...`
    * This is because `paramiko` library doesn't support latest format "RFC4716"

### Configuration examples

Example1:

```
[~/.ssh/config]
Host myserver
  HostName myserver.example.com
  User admin
  Port 2222
  IdentityFile ~/.ssh/id_rsa_myserver
  ForwardAgent yes

Host *
  User ubuntu
```

Example2:

```
[~/.ssh/config]
Host another-server
  HostName 192.0.2.1
```

Minimal example:

```
[~/.ssh/config]

# If you specify a FQDN / IP address, same login user, and discoverable private key,
# no configuration needed
```

See also a tutorial above in detail.

## Parameterized run

See [examples/parameterized-notebook](https://github.com/NII-cloud-operation/sshkernel/blob/master/examples/parameterized-notebook.ipynb).

## Limitations

* As Jupyter Notebook has limitation to handle `stdin`,
  you may need to change some server configuration and commands to avoid *interactive input*.
  * e.g. use publickey-authentication instead of password, enable NOPASSWD for sudo, use `expect`
* Some shell variables are different from normal interactive shell
  * e.g. `$?`, `$$`

## LICENSE

This software is released under the terms of the Modified BSD License.

[Logo](https://commons.wikimedia.org/wiki/File:High-contrast-utilities-terminal.png) from Wikimedia Commons is licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0).
