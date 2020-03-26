import os
import time

import paramiko

from plumbum.machines.paramiko_machine import ParamikoMachine

import yaml

from .ssh_wrapper import SSHWrapper


class SSHWrapperPlumbum(SSHWrapper):
    """
    A plumbum remote machine wrapper
    SSHWrapperPlumbum wraps ssh client.

    Attributes:
    * ._remote : plumbum.machines.paramiko_machine.ParamikoMachine
    * ._remote._client: paramiko.SSHClient
    """

    def __init__(self, envdelta_init=dict()):
        self.envdelta_init = envdelta_init
        self._remote = None
        self.__connected = False
        self._host = ""
        self.interrupt_function = lambda: None

    def exec_command(self, cmd, print_function):
        """
        Returns:
          int: exit_code
            * Return the last command exit_code
            * Return 1 if failed to execute a command

        Raises:
            plumbum.commands.processes.ProcessExecutionError: If exit_code is 0
        """

        print_function("[ssh] host = {}, cwd = {}\n".format(self._host, self.get_cwd()))

        marker = str(time.time())[::-1]
        full_command = append_footer(cmd, marker)

        proc = self._remote["bash"]["-c", full_command].popen()
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

        envdelta = {**self.envdelta_init, "PAGER": "cat"}
        remote.env.update(envdelta)

        self._remote = remote
        self.__connected = True
        self._host = host

    def _build_remote(self, host):
        (hostname, plumbum_kwargs, forward_agent) = load_ssh_config_for_plumbum(
            "~/.ssh/config", host
        )

        print(
            "[ssh] host={host} hostname={hostname} other_conf={other_conf}".format(
                host=host, hostname=hostname, other_conf=plumbum_kwargs
            )
        )

        remote = ParamikoMachine(hostname, password=None, **plumbum_kwargs)

        if forward_agent == "yes":
            print("[ssh] forwarding local agent")
            enable_agent_forwarding(remote._client)

        return remote

    def close(self):
        self.__connected = False

        if self._remote:
            self._remote.close()

    def interrupt(self):
        self.interrupt_function()

    def isconnected(self):
        return self.__connected

    # private methods
    def _update_interrupt_function(self, proc):
        def to_interrupt():
            proc.close()

        self.interrupt_function = to_interrupt

    def post_exec_command(self, env_out):
        """Receive yaml string, update instance state with its value

        Return:
            int: exit_code
        """
        env_at_footer = yaml.load(env_out)

        newdir = env_at_footer["pwd"]
        newenv = env_at_footer["env"]
        self.update_workdir(newdir)
        self.update_env(newenv)

        if "code" in env_at_footer:
            return env_at_footer["code"]
        else:
            print("[ssh] Error: Cannot parse exit_code. As a result, returing code=1")
            return 1

    def update_workdir(self, newdir):
        cwd = self.get_cwd()
        if newdir != cwd:
            self._remote.cwd.chdir(newdir)
            print("[ssh] new cwd: {}".format(newdir))

    def get_cwd(self):
        return self._remote.cwd.getpath()._path

    def update_env(self, newenv):
        delimiter = "^@"
        reject_env_variables = ["SSH_CLIENT", "SSH_CONNECTION"]

        parsed_newenv = dict([kv.split("=", 1) for kv in newenv.split(delimiter) if kv])
        parsed_newenv = {
            k: v for k, v in parsed_newenv.items() if k not in reject_env_variables
        }

        self._remote.env.update(parsed_newenv)


def append_footer(cmd, marker):
    """
    Append header/footer to `cmd`.

    Returns:
        str: new_command
    """
    header = ""
    footer = """
EXIT_CODE=$?
echo {marker}code: ${{EXIT_CODE}}{marker}
echo {marker}pwd: $(pwd){marker}
echo {marker}env: $(cat -v <(env -0)){marker}
""".format(
        marker=marker
    )

    full_command = "\n".join([header, cmd, footer])

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

    env_out = ""
    for line in iterator:

        if line.endswith(marker + "\n"):

            if not line.startswith(marker):
                # The `line` contains 2 markers and trailing newline
                # e.g "123MARKcode: 0MARK\n".split(marker) =>  ("123", "code: 0", "\n")
                line1, line2, _ = line.split(marker)
                print_function(line1)
                line = line2

            env_out += line.replace(marker, "").rstrip()
            env_out += "\n"

        else:
            print_function(line)

    return env_out


def enable_agent_forwarding(paramiko_sshclient):
    # SSH Agent Forwarding in Paramiko
    # http://docs.paramiko.org/en/stable/api/agent.html#paramiko.agent.AgentRequestHandler
    sess = paramiko_sshclient.get_transport().open_session()
    paramiko.agent.AgentRequestHandler(sess)


def load_ssh_config_for_plumbum(filename, host):
    """Parse and postprocess ssh_config
    and rename some keys for plumbum.ParamikoMachine.__init__()
    """

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
        load_system_ssh_config=False,
        # TODO: Drop WarningPolicy
        # This is need in current plumbum and wrapper implementation
        # in case proxycommand is set.
        missing_host_policy=paramiko.WarningPolicy(),
    )

    plumbum_host = host
    if "hostname" in lookup:
        plumbum_host = lookup.get("hostname")

    if "port" in lookup:
        plumbum_kwargs["port"] = int(lookup["port"])

    plumbum_kwargs["user"] = lookup.get("user")
    plumbum_kwargs["keyfile"] = lookup.get("identityfile")

    if "proxycommand" in lookup:
        plumbum_kwargs["load_system_ssh_config"] = True
        # load_system_ssh_config: read system SSH config for ProxyCommand configuration.
        # https://plumbum.readthedocs.io/en/latest/_modules/plumbum/machines/paramiko_machine.html

        if lookup.get("hostname") != host:
            msg = (
                "can't handle both ProxyCommand and HostName at once, "
                "please drop either"
            )
            raise ValueError(msg)
        plumbum_host = host
        # When load_system_ssh_config is True, plumbum_host must be Host
        # instead of HostName.
        # Otherwise parsing SSH config will fail in Plumbum.

    # Plumbum doesn't support agent-forwarding
    forward_agent = lookup.get("forwardagent")

    return (plumbum_host, plumbum_kwargs, forward_agent)
