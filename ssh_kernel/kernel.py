from abc import ABC, abstractmethod
from logging import INFO
import os
import re

from ipykernel.kernelbase import Kernel
from paramiko.ssh_exception import SSHException
import paramiko

from metakernel import ExceptionWrapper
from metakernel import MetaKernel

from .exception import SSHKernelNoConnectedException
from .magics import register_magics

__version__ = '0.1.0'

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class SSHWrapper(ABC):
    @abstractmethod
    def exec_command(self, cmd):
        '''
        Returns:
            io.TextIOWrapper: Command output stream
        '''

    @abstractmethod
    def exit_code(self):
        '''
        Returns:
            int: Previous comamand exit code
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

    def exec_command(self, cmd):
        # fixme: raise unless _client.connect() is not succeeded

        # FIXME:
        # Wrap paramiko.BufferedFile to return UTF-8 string stream always
        # Currently, f.read() is bytes stream, and f.readlines() is string.

        #
        # FIXME: get_pty has pager problem
        i, o, e = self._client.exec_command(cmd, get_pty=True)

        # `get_pty` make stderr print in stdin
        # so we can close stderr immediately
        i.close()
        e.close()

        return o

    def exit_code(self):
        # Not implemented yet
        return 0

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
        conf = paramiko.config.SSHConfig()
        with open(os.path.expanduser(filename)) as ssh_config:
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

        return (hostname, lookup)


class SSHKernel(MetaKernel):
    '''
    SSH kernel run commands remotely

    Forked from bash_kernel
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.silent = False

        # TODO: Survey logging architecture, should not depend on parent.log
        self.log.name = 'SSHKernel'
        self.log.setLevel(INFO)
        self.redirect_to_log = True
        self.sshwrapper = SSHWrapperParamiko()

    def reload_magics(self):
        # todo: Avoid depend on private method
        super().reload_magics()
        register_magics(self)

    def process_output(self, stream):
        if not self.silent:
            for line in stream:
                self.Write(line)

    ##############################
    # Implement base class methods
    def do_execute_direct(self, code, silent=False):
        try:
            self.assert_connected()
        except SSHKernelNoConnectedException as e:
            return ExceptionWrapper('abort', 'not connected', [])

        interrupted = False
        try:
            o = self.sshwrapper.exec_command(code)
            self.process_output(o)

        except KeyboardInterrupt:
            interrupted = True
            self.Error('* interrupt...')
            #
            # FIXME: sendintr

            #
            # TODO: Return more information
            return ExceptionWrapper('abort', str(1), [str(KeyboardInterrupt)])

        except SSHException:
            #
            # FIXME: Implement reconnect sequence
            return ExceptionWrapper('ssh_exception', str(1), [])

        try:
            exitcode = self.sshwrapper.exit_code()
        except Exception as e:
            #
            # FIXME: Don't catch Exception
            exitcode = 1
            traceback = str(e)

        if exitcode:
            ename = ''
            evalue = str(exitcode)
            if 'traceback' not in locals():
                traceback = ''

            return ExceptionWrapper(ename, evalue, traceback)

    def do_complete(self, code, cursor_pos):
        try:
            self.assert_connected()
        except SSHKernelNoConnectedException as e:
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
            o = self.sshwrapper.exec_command(cmd)
            completions = set(o.readlines())
            # append matches including leading $
            matches = ['$'+c for c in completions]
        else:
            # complete functions and builtins
            cmd = 'compgen -cdfa %s' % token
            o = self.sshwrapper.exec_command(cmd)
            matches = set(o.readlines())
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
        Check client is connected or raise.
        '''

        if not self.sshwrapper.isconnected():
            self.Error('Not connected')
            raise SSHKernelNoConnectedException


    def Login(self, host):
        """
        %login magic handler.

        Returns:
            string: Message
            bool: Falsy if succeeded
        """

        #
        # FIXME: Handle error
        #
        self.sshwrapper.connect(host)

        msg = 'Successfully logged in.'
        err = None

        return (msg, err)
