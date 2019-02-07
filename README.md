# sshkernel

SSH Kernel for Jupyter notebook.

## Requirements

* Python3.5+
* IPython 7.0+

## Installation

```
pip install -U sshkernel
python -m sshkernel install [--user]
# Install a kernel specification directory.
# Type `python -msshkernel install --help` for more information.
```

## Tutorial (in Japanese)

* [ssh-kernel-how-to](doc/ssh-kernel-how-to.ipynb)

## Configuration

SSH Kernel obtains configuration data from `~/.ssh/config` file to connect servers.

Possible keywords are as follows:

* HostName
* User
* Port
* IdentityFile

### Notes about private keys

* If you use a ed25519 key, please generate with or convert into old PEM format
    * e.g. `ssh-keygen -m PEM -t ed25519 ...`
    * This is because `paramiko` library doesn't support latest format "RFC4716"
* As private key files in `~/.ssh/` are discoverable, you do not necessarily specify `IdentityFile`

### Configuration examples

Example1:

```
[~/.ssh/config]
Host myserver
  HostName myserver.example.com
  User admin
  Port 2222
  IdentityFile ~/.ssh/id_rsa_myserver
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

## LICENSE

This software is released under the terms of the Modified BSD License.
