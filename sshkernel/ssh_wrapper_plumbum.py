from types import MappingProxyType
import os
import time
import yaml

import paramiko
from plumbum.commands.base import shquote
from plumbum.machines.paramiko_machine import ParamikoMachine

from .ssh_wrapper import SSHWrapper


class SSHWrapperPlumbum(SSHWrapper):
    '''
    A plumbum remote machine wrapper
    '''

    def __init__(self, envdelta_init=dict()):
        self.envdelta_init = MappingProxyType(dict((k, shquote(v)) for k,v in envdelta_init.items()))
        self._remote = None
        self._connected = False
        self._host = ''
        self.interrupt_function = lambda: None

    def exec_command(self, cmd, print_function):
        '''
        Returns:
          int: exit_code
            * Return the last command exit_code
            * Return 1 if failed to execute a command

        Raises:
            plumbum.commands.processes.ProcessExecutionError: If exit_code is 0
        '''

        print_function('[ssh] host = {}, cwd = {}\n'.format(self._host, self.get_cwd()))

        marker = str(time.time())[::-1]
        full_command = append_footer(cmd, marker)

        proc = self._remote['bash'][
            '-c',
            full_command,
        ].popen()
        self._update_interrupt_function(proc)

        tuple_iterator = proc.iter_lines()
        env_info = process_output(tuple_iterator, marker, print_function)

        if env_info:
            return self.post_exec_command(env_info)
        else:
            return 1

    def connect(self, host):
        if self._remote:
            self.close()

        remote = self._build_remote(host)

        envdelta = {**self.envdelta_init, 'PAGER': 'cat'}
        remote.env.update(envdelta)

        self._remote = remote
        self._connected = True
        self._host = host

    def _forward_local_agent(self, paramiko_client):
        # SSH Agent Forwarding in Paramiko
        # http://docs.paramiko.org/en/2.4/api/agent.html
        sess = paramiko_client.get_transport().open_session()
        paramiko.agent.AgentRequestHandler(sess)

    def _build_remote(self, host):
        (hostname, plumbum_kwargs, forward_agent) = self._load_ssh_config_for_plumbum('~/.ssh/config', host)

        print('[ssh] host={host} hostname={hostname} other_conf={other_conf}'.format(
            host=host,
            hostname=hostname,
            other_conf=plumbum_kwargs,
        ))

        remote = ParamikoMachine(hostname, password=None, **plumbum_kwargs)

        if forward_agent == 'yes':
            print('[ssh] forwarding local agent')
            self._forward_local_agent(remote._client)

        return remote

    def close(self):
        self._connected = False

        if self._remote:
            self._remote.close()

    def interrupt(self):
        self.interrupt_function()

    def isconnected(self):
        return self._connected

    # private methods
    def _update_interrupt_function(self, proc):
        def to_interrupt():
            proc.close()

        self.interrupt_function = to_interrupt

    def post_exec_command(self, env_out):
        '''Receive yaml string, update instance state with its value

        Return:
            int: exit_code
        '''
        env_at_footer = yaml.load(env_out)

        newdir = env_at_footer['pwd']
        newenv = env_at_footer['env']
        self.update_workdir(newdir)
        self.update_env(newenv)

        if 'code' in env_at_footer:
            return env_at_footer['code']
        else:
            print('[ssh] Error: Cannot parse exit_code. As a result, returing code=1')
            return 1

    def update_workdir(self, newdir):
        cwd = self.get_cwd()
        if newdir != cwd:
            self._remote.cwd.chdir(newdir)
            print('[ssh] new cwd: {}'.format(newdir))

    def get_cwd(self):
        return self._remote.cwd.getpath()._path

    def update_env(self, newenv):
        delimiter = '^@'
        parsed_newenv = dict([
            kv.split('=', 1) for kv in newenv.split(delimiter) if kv
        ])

        #
        # Although RemoteEnv.update() calls shquote() internally,
        # it is ignored with ParamikoMachine.
        # So I quote manually here.
        quoted_newenv = dict([
            (k, shquote(v)) for k,v in parsed_newenv.items()
        ])

        self._remote.env.update(quoted_newenv)

    def _load_ssh_config_for_plumbum(self, filename, host):
        '''Parse and postprocess ssh_config
        '''

        conf = paramiko.config.SSHConfig()
        expanded_path = os.path.expanduser(filename)

        if os.path.exists(expanded_path):
            with open(expanded_path) as ssh_config:
                conf.parse(ssh_config)

        lookup = conf.lookup(host)

        plumbum_kwargs = dict(
            user=None,
            port=None,
            keyfile=None,
        )

        if 'hostname' in lookup:
            plumbum_hostname = lookup.pop('hostname')
        else:
            plumbum_hostname = host

        if 'port' in lookup:
            plumbum_kwargs['port'] = int(lookup['port'])

        plumbum_kwargs['user'] = lookup.get('user')
        plumbum_kwargs['keyfile'] = lookup.get('identityfile')

        forward_agent = lookup.get('forwardagent')

        return (plumbum_hostname, plumbum_kwargs, forward_agent)

def append_footer(cmd, marker):
    '''
    Append header/footer to `cmd`.

    Returns:
        str: new_command
    '''
    header = ''
    footer = '''
EXIT_CODE=$?
echo {marker}code: ${{EXIT_CODE}}{marker}
echo {marker}pwd: $(pwd){marker}
echo {marker}env: $(cat -v <(env -0)){marker}
'''.format(marker=marker)

    full_command = '\n'.join([header, cmd, footer])

    return full_command

def merge_stdout_stderr(iterator):
    """Merge two iterators returned by Popen.communicate()

    Args:
        iterator: yields (string, string), either one of two string is None

    Returns:
        iterator: yields string
    """

    for (stdout, stderr) in iterator:
        if stdout:
            yield stdout
        else:
            yield stderr

def process_output(tuple_iterator, marker, print_function):
    """Process iterator which is return of Popen.communicate()

    For normal lines, call callback print-fn.

    Args:
        tuple_iterator: yields tuple (string, string)
        print_function: callback fn

    Returns:
        string: footer string (YAML format)
    """

    iterator = merge_stdout_stderr(tuple_iterator)

    env_out = ''
    for line in iterator:

        if line.endswith(marker + "\n"):

            if not line.startswith(marker):
                # The `line` contains 2 markers and trailing newline
                #
                line1, line2, _ = line.split(marker) # "123MARKcode: 0MARK\n" splitted into ("123", "code: 0", "\n")
                print_function(line1)
                line = line2

            env_out += line.replace(marker, '').rstrip()
            env_out += "\n"

        else:
            print_function(line)

    return env_out
