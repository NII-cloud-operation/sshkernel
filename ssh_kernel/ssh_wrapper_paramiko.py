import os

import paramiko

from .ssh_wrapper import SSHWrapper


class SSHWrapperParamiko(SSHWrapper):

    def __init__(self):
        self._client = None
        self._connected = False

    def exec_command(self, cmd, print_function):
        bufsize = -1
        timeout = None
        get_pty = True
        environment = None
        trans = self._client.get_transport()
        chan = trans.open_session(timeout=timeout)

        if get_pty:
            chan.get_pty()
        chan.settimeout(timeout)
        if environment:
            chan.update_environment(environment)
        chan.exec_command(cmd)
        out = chan.makefile("r", bufsize)
        #stdin = chan.makefile("wb", bufsize)
        #stderr = chan.makefile_stderr("r", bufsize)

        #
        # Note: With `get_pty`, `out` has both STDOUT and STDERR
        for line in out:
            print_function(line)

        return chan.recv_exit_status()

    def connect(self, host):
        if self._client:
            self.close()

        client = self._new_paramiko_client()
        hostname, lookup = self._init_ssh_config('~/.ssh/config', host)

        # Authentication is attempted in the following order of priority:
        # * The pkey or key_filename passed in (if any)
        # * Any key we can find through an SSH agent
        # * Any “id_rsa”, “id_dsa” or “id_ecdsa” key discoverable in ~/.ssh/
        #
        # http://docs.paramiko.org/en/2.4/api/client.html

        print(lookup)

        client.connect(hostname, **lookup)

        self._client = client
        self._connected = True

    def _new_paramiko_client(self):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        return client

    def close(self):
        self._connected = False
        self._client.close()

    def interrupt(self):
        pass

    def isconnected(self):
        return self._connected

    def _init_ssh_config(self, filename, host):
        supported_fields = [
            'key_filename',
            'port',
            'username',
        ]
        conf = paramiko.config.SSHConfig()
        expanded_path = os.path.expanduser(filename)

        if os.path.exists(expanded_path):
            with open(expanded_path) as ssh_config:
                conf.parse(ssh_config)

        lookup = conf.lookup(host)

        if 'hostname' in lookup:
            hostname = lookup.pop('hostname')
        else:
            hostname = host

        if 'identityfile' in lookup:
            lookup['key_filename'] = lookup.pop('identityfile')
        if 'port' in lookup:
            lookup['port'] = int(lookup.pop('port'))
        if 'user' in lookup:
            lookup['username'] = lookup.pop('user')

        keys_filtered = set(supported_fields) & set(lookup.keys())
        lookup_filtered = dict((k, lookup[k]) for k in keys_filtered)

        return (hostname, lookup_filtered)
