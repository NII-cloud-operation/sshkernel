from logging import INFO
from textwrap import dedent
import os
import re
import sys
import traceback

from ipykernel.kernelbase import Kernel
from paramiko.ssh_exception import SSHException

from metakernel import ExceptionWrapper
from metakernel import MetaKernel

from . import __version__
from .exception import SSHKernelNotConnectedException
from .magics import register_magics
from .ssh_wrapper_plumbum import SSHWrapperPlumbum

version_pat = re.compile(r'version (\d+(\.\d+)+)')


class SSHKernel(MetaKernel):
    '''
    SSH kernel run commands remotely.
    '''
    implementation = 'sshkernel'
    implementation_version = __version__
    language = 'bash'
    language_info = {}
    kernel_json = {
        'argv': [sys.executable, '-m', 'sshkernel', '-f', '{connection_file}'],
        'display_name': 'SSH',
        'language': 'bash',
        'codemirror_mode': 'shell',
        'env': {'PS1': '$'},
        'name': 'ssh',
    }

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
        self._sshwrapper = value

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
        self._sshwrapper = None
        self._parameters = dict()

    def set_param(self, key, value):
        '''
        Set sshkernel parameter for hostname and remote envvars.
        '''

        self._parameters[key] = value

    def get_params(self):
        '''
        Get sshkernel parameters dict.
        '''

        return self._parameters


    def new_ssh_wrapper(self):
        '''
        Instanciate wrapper instance

        Call close() if exist.
        '''

        self.del_ssh_wrapper()

        self.sshwrapper = SSHWrapperPlumbum(self.get_params())

    def del_ssh_wrapper(self):
        '''
        Gracefully delete wrapper instance
        '''

        if self.sshwrapper:
            self.Print('[ssh] Closing existing connection.')

            # TODO: error handling
            self.sshwrapper.close()

        self.sshwrapper = None

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

            # TODO: Handle exception
            self.sshwrapper.interrupt()

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
    def get_completions(self, info):
        # info: Dict = self.parse_code(code, 0, cursor_pos)
        code = info['line']
        cursor_pos = info['column']

        default = []

        try:
            self.assert_connected()
        except SSHKernelNotConnectedException as e:
            # TODO: Error() in `do_complete` not shown in notebook
            self.log.error('not connected')
            return default

        code = code[:cursor_pos]

        if not code or code[-1] == ' ':
            return default

        tokens = code.replace(';', ' ').split()
        if not tokens:
            return default

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

        matches = [m for m in matches if m.startswith(token)]

        return matches

    def restart_kernel(self):
        # TODO: log message
        # self.Print('[INFO] Restart sshkernel ...')

        self.del_ssh_wrapper()
        self._parameters = dict()

    def assert_connected(self):
        '''
        Assert client is connected.
        '''

        if self.sshwrapper is None:
            self.Error('[ssh] Not logged in.')
            raise SSHKernelNotConnectedException
        elif not self.sshwrapper.isconnected():
            self.Error('[ssh] Not connected.')
            raise SSHKernelNotConnectedException
