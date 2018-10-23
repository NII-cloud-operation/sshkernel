from abc import ABC, abstractmethod
import io
from subprocess import check_output
import os
import re

from ipykernel.kernelbase import Kernel
from paramiko.ssh_exception import SSHException
import paramiko

from metakernel import ExceptionWrapper
from metakernel import MetaKernel

from .magics import register_magics

__version__ = '0.1.0'

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class SSHWrapper(ABC):
    @abstractmethod
    def exec_command(self, cmd):
        '''
        Returns:
            string: Command output
        '''
        raise NotImplementedError

    @abstractmethod
    def exit_code(self):
        '''
        Returns:
            int: Previous comamand exit code
        '''
        raise NotImplementedError

    @abstractmethod
    def connect(self, host):
        '''
        Connect to host

        Raises:
            SSHConnectionError
        '''
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def interrupt(self):
        '''
        Send SIGINT to remote
        '''
        raise NotImplementedError



class SSHWrapperParamiko(SSHWrapper):
    def __init__(self):
        self._client = None

    def exec_command(self, cmd):
        # fixme: raise unless host is set

        # todo: Merge stderr into stdout, or append '2>&1'
        _, o, _ = self._client.exec_command(cmd)

        return io.TextIOWrapper(o, encoding='utf-8')

    def exit_code(self):
        # Not implemented yet
        return 0

    def connect(self, host):
        if self._client:
            self.close()

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        config = self._init_ssh_config('~/.ssh/config')
        lookup = config.lookup(host)

        # Authentication is attempted in the following order of priority:
        # * The pkey or key_filename passed in (if any)
        # * Any key we can find through an SSH agent
        # * Any “id_rsa”, “id_dsa” or “id_ecdsa” key discoverable in ~/.ssh/
        #
        # http://docs.paramiko.org/en/2.4/api/client.html

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

        print(lookup)

        client.connect(hostname, **lookup)

        self._client = client

    def close(self):
        self._client.close()

    def interrupt(self):
        pass

    def _init_ssh_config(self, filename):
        conf = paramiko.config.SSHConfig()
        with open(os.path.expanduser(filename)) as ssh_config:
            conf.parse(ssh_config)

        return conf


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

        self.sshwrapper = SSHWrapperParamiko()

    def reload_magics(self):
        # todo: Avoid depend on private method
        super().reload_magics()
        register_magics(self)

    def process_output(self, stream):
        if not self.silent:
            for line in stream:
                stream_content = {'name': 'stdout', 'text': line}
                self.send_response(self.iopub_socket, 'stream', stream_content)

    ##############################
    # Implement base class methods
    def do_execute_direct(self, code, silent=False):
        interrupted = False
        try:
            o = self.sshwrapper.exec_command(code)
            self.process_output(o)

        except KeyboardInterrupt:
            # todo: sendintr
            # Use paramiko.Channel directly instead of paramiko.Client

            interrupted = True
            self.Error('* interrupt')

        except SSHException:
            # todo: Implement reconnect sequence
            output = 'Reconnect SSH...'
            self.sshwrapper.connect()
            self.Error(output)

        if interrupted:
            # todo: Return more information
            return ExceptionWrapper('abort', str(1), [str(KeyboardInterrupt)])

        try:
            exitcode = self.sshwrapper.exit_code()
        except Exception as e:
            exitcode = 1
            traceback = str(e)

        if exitcode:
            ename = ''
            evalue = str(exitcode)
            if not traceback:
                traceback = ''

            return ExceptionWrapper(ename, evalue, traceback)

    def do_complete(self, code, cursor_pos):
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
            cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:] # strip leading $
            output = self.sshwrapper.exec_command(cmd).read().rstrip()
            completions = set(output.split())
            # append matches including leading $
            matches.extend(['$'+c for c in completions])
        else:
            # complete functions and builtins
            cmd = 'compgen -cdfa %s' % token
            o = self.sshwrapper.exec_command(cmd)
            output = o.read().rstrip()
            matches.extend(output.split())

        if not matches:
            return default
        matches = [m for m in matches if m.startswith(token)]

        return {'matches': sorted(matches), 'cursor_start': start,
                'cursor_end': cursor_pos, 'metadata': dict(),
                'status': 'ok'}

    def restart_kernel(self):
        self.Print('[ssh] Restart kernel: Closing connection...')
        self.sshwrapper.close()

    def Login(self, host):
        """
        %login magic handler.

        Returns:
            string: Message
            bool: Falsy if succeeded
        """

        self.sshwrapper.connect(host)

        msg = 'Successfully logged in.'
        err = None

        return (msg, err)
