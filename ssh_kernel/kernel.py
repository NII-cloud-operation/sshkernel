from abc import ABC, abstractmethod
from logging import INFO
from textwrap import dedent
import os
import re
import traceback

from ipykernel.kernelbase import Kernel
from paramiko.ssh_exception import SSHException
import paramiko

from metakernel import ExceptionWrapper
from metakernel import MetaKernel

from . import __version__
from .exception import SSHKernelNotConnectedException
from .magics import register_magics

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class SSHWrapper(ABC):
    @abstractmethod
    def exec_command(self, cmd, print_function):
        '''
        Args:
            cmd (string)
            print_function (lambda)

        Returns:
            int: exit code
        '''

    @abstractmethod
    def connect(self, host):
        '''
        Connect to host

        Raises:
            SSHConnectionError
        '''

    @abstractmethod
    def close(self):
        '''
        Close connection to host
        '''

    @abstractmethod
    def interrupt(self):
        '''
        Send SIGINT to halt current execution
        '''

    @abstractmethod
    def isconnected(self):
        '''
        Connected to host or not

        Returns:
            bool
        '''


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


class SSHKernel(MetaKernel):
    '''
    SSH kernel run commands remotely.
    '''
    implementation = 'ssh_kernel'
    implementation_version = __version__

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None

    @property
    def banner(self):
        if self._banner is None:
            self._banner = 'SSH kernel version {}'.format(__version__)
        return self._banner

    language_info = {'name': 'ssh',
                     'codemirror_mode': 'shell',
                     'mimetype': 'text/x-sh',
                     'file_extension': '.sh'}

    @property
    def sshwrapper(self):
        return self._sshwrapper

    @sshwrapper.setter
    def sshwrapper(self, value):
        self._ssh_wrapper = value

    def get_usage(self):
        return dedent('''Usage:

        * Prepare `~/.ssh/config`
        * To login to the remote server, use magic command `%login <host_in_ssh_config>` into a new cell
            * e.g. `%login localhost`
        * After %login, input commands are executed remotely
        * To close session, use `%logout` magic command
        ''')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.silent = False

        # TODO: Survey logging architecture
        self.log.name = 'SSHKernel'
        self.log.setLevel(INFO)
        self.redirect_to_log = True
        self._sshwrapper = SSHWrapperParamiko()

    def reload_magics(self):
        super().reload_magics()
        register_magics(self)

    # Implement base class method
    def do_execute_direct(self, code, silent=False):
        try:
            self.assert_connected()
        except SSHKernelNotConnectedException as e:
            self.Error(traceback.format_exc())
            return ExceptionWrapper('abort', 'not connected', [])

        try:
            exitcode = self.sshwrapper.exec_command(code, self.Write)

        except KeyboardInterrupt:
            self.Error('* interrupt...')
            #
            # FIXME: sendintr

            self.Error(traceback.format_exc())

            return ExceptionWrapper('abort', str(1), [str(KeyboardInterrupt)])

        except SSHException:
            #
            # TODO: Implement reconnect sequence
            return ExceptionWrapper('ssh_exception', str(1), [])

        if exitcode:
            ename = 'abnormal exit code'
            evalue = str(exitcode)
            if 'tb' not in locals():
                tb = ['']

            return ExceptionWrapper(ename, evalue, tb)

    # Implement base class method
    def do_complete(self, code, cursor_pos):
        try:
            self.assert_connected()
        except SSHKernelNotConnectedException as e:
            # TODO: Error() in `do_complete` not shown in notebook
            self.log.error('not connected')

            content = {
                'matches': [],
                'metadata': {},
                'status': 'ok',
            }
            return content

        code = code[:cursor_pos]
        default = {'matches': [], 'cursor_start': 0,
                   'cursor_end': cursor_pos, 'metadata': dict(),
                   'status': 'ok'}

        if not code or code[-1] == ' ':
            return default

        tokens = code.replace(';', ' ').split()
        if not tokens:
            return default

        matches = []
        token = tokens[-1]
        start = cursor_pos - len(token)

        if token[0] == '$':
            # complete variables

            # strip leading $
            cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:]
            completions = set()
            callback = lambda line: completions.add(line.rstrip())
            self.sshwrapper.exec_command(cmd, callback)

            # append matches including leading $
            matches = ['$'+c for c in completions]
        else:
            # complete functions and builtins
            cmd = 'compgen -cdfa %s' % token
            matches = set()
            callback = lambda line: matches.add(line.rstrip())
            self.sshwrapper.exec_command(cmd, callback)

        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}

    def restart_kernel(self):
        self.Print('[ssh] Restart kernel: Closing connection...')
        self.sshwrapper.close()

    def assert_connected(self):
        '''
        Assert client is connected.
        '''

        if not self.sshwrapper.isconnected():
            self.Error('[ssh] Not connected')
            raise SSHKernelNotConnectedException
