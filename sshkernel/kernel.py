import re
import sys
import textwrap
import traceback
from logging import INFO

from metakernel import ExceptionWrapper
from metakernel import MetaKernel

from paramiko.ssh_exception import SSHException

from .exception import SSHKernelNotConnectedException
from .ssh_wrapper_plumbum import SSHWrapperPlumbum
from .version import __version__

version_pat = re.compile(r"version (\d+(\.\d+)+)")


class SSHKernel(MetaKernel):
    """
    SSH kernel run commands remotely.
    """

    implementation = "sshkernel"
    implementation_version = __version__
    language = "bash"
    language_version = __version__
    banner = "SSH kernel version {}".format(__version__)
    kernel_json = {
        "argv": [sys.executable, "-m", "sshkernel", "-f", "{connection_file}"],
        "display_name": "SSH",
        "language": "bash",
        "codemirror_mode": "shell",
        "env": {"PS1": "$"},
        "name": "ssh",
    }
    language_info = {
        "name": "ssh",
        "codemirror_mode": "shell",
        "mimetype": "text/x-sh",
        "file_extension": ".sh",
    }

    @property
    def sshwrapper(self):
        return self._sshwrapper

    @sshwrapper.setter
    def sshwrapper(self, value):
        self._sshwrapper = value

    def get_usage(self):
        return textwrap.dedent(
            """Usage:

        * Prepare `~/.ssh/config`
        * To login to the remote server, use magic command `%login <host_in_ssh_config>` into a new cell
            * e.g. `%login localhost`
        * After %login, input commands are executed remotely
        * To close session, use `%logout` magic command
        """
        )

    def __init__(self, sshwrapper_class=SSHWrapperPlumbum, **kwargs):
        super().__init__(**kwargs)

        self.__sshwrapper_class = sshwrapper_class
        self._sshwrapper = None
        self._parameters = dict()

        # Touch inherited attribute
        self.log.name = "SSHKernel"
        self.log.setLevel(INFO)

    def set_param(self, key, value):
        """
        Set sshkernel parameter for hostname and remote envvars.
        """

        self._parameters[key] = value

    def get_params(self):
        """
        Get sshkernel parameters dict.
        """

        return self._parameters

    def do_login(self, host: str):
        """Establish a ssh connection to the host."""
        self.do_logout()

        wrapper = self.__sshwrapper_class(self.get_params())
        self.sshwrapper = wrapper
        self.sshwrapper.connect(host)

    def do_logout(self):
        """Close the connection."""
        if self.sshwrapper:
            self.Print("[ssh] Closing existing connection.")
            self.sshwrapper.close()  # TODO: error handling
            self.Print("[ssh] Successfully logged out.")

        self.sshwrapper = None

    # Implement base class method
    def do_execute_direct(self, code, silent=False):
        try:
            self.assert_connected()
        except SSHKernelNotConnectedException:
            self.Error(traceback.format_exc())
            return ExceptionWrapper("abort", "not connected", [])

        try:
            exitcode = self.sshwrapper.exec_command(code, self.Write)

        except KeyboardInterrupt:
            self.Error("* interrupt...")

            # TODO: Handle exception
            self.sshwrapper.interrupt()

            self.Error(traceback.format_exc())

            return ExceptionWrapper("abort", str(1), [str(KeyboardInterrupt)])

        except SSHException:
            #
            # TODO: Implement reconnect sequence
            return ExceptionWrapper("ssh_exception", str(1), [])

        if exitcode:
            ename = "abnormal exit code"
            evalue = str(exitcode)
            trace = [""]

            return ExceptionWrapper(ename, evalue, trace)

        return None

    # Implement ipykernel method
    def do_complete(self, code, cursor_pos):
        default = {
            "matches": [],
            "cursor_start": 0,
            "cursor_end": cursor_pos,
            "metadata": dict(),
            "status": "ok",
        }
        try:
            self.assert_connected()
        except SSHKernelNotConnectedException:
            # TODO: Error() in `do_complete` not shown in notebook
            self.log.error("not connected")
            return default

        code_current = code[:cursor_pos]
        if not code_current or code_current[-1] == " ":
            return default

        tokens = code_current.replace(";", " ").split()
        if not tokens:
            return default

        token = tokens[-1]

        if token[0] == "$":
            # complete variables

            # strip leading $
            cmd = "compgen -A arrayvar -A export -A variable %s" % token[1:]
            completions = set()

            def callback(line):
                completions.add(line.rstrip())

            self.sshwrapper.exec_command(cmd, callback)

            # append matches including leading $
            matches = ["$" + c for c in completions]
        else:
            # complete functions and builtins
            cmd = "compgen -cdfa %s" % token
            matches = set()

            def callback(line):
                matches.add(line.rstrip())

            self.sshwrapper.exec_command(cmd, callback)

        matches = [m for m in matches if m.startswith(token)]

        cursor_start = cursor_pos - len(token)
        cursor_end = cursor_pos

        return dict(
            matches=sorted(matches),
            cursor_start=cursor_start,
            cursor_end=cursor_end,
            metadata=dict(),
            status="ok",
        )

    def restart_kernel(self):
        # TODO: log message
        # self.Print('[INFO] Restart sshkernel ...')

        self.do_logout()
        self._parameters = dict()

    def assert_connected(self):
        """
        Assert client is connected.
        """

        if self.sshwrapper is None:
            self.Error("[ssh] Not logged in.")
            raise SSHKernelNotConnectedException

        if not self.sshwrapper.isconnected():
            self.Error("[ssh] Not connected.")
            raise SSHKernelNotConnectedException
