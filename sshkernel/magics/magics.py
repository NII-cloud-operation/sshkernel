import re
import sys
import traceback

from metakernel import ExceptionWrapper
from metakernel import Magic


class SSHKernelMagics(Magic):
    def line_login(self, host):
        """
        %login HOST

        SSH login to the remote host.
        Cells below this line will be executed remotely.

        Example:
            [~/.ssh/config]
            Host myserver
                Hostname 10.0.0.10
                Port 2222

            %login myserver
        """

        self.retval = None
        try:
            self.kernel.Print("[ssh] Login to {}...".format(host))

            expanded_host = expand_parameters(host, self.kernel.get_params())
            self.kernel.do_login(expanded_host)
        except Exception as exc:
            self.kernel.Error("[ssh] Login to {} failed.".format(host))
            self.kernel.Error(exc)

            tb = traceback.format_exc().splitlines()

            # (name, value, tb)
            self.retval = ExceptionWrapper(
                "SSHConnectionError", "Login to {} failed.".format(host), tb
            )
        else:
            self.kernel.Print("[ssh] Successfully logged in.")

    def line_logout(self):
        """
        %logout

        Logout and disconnect.

        Example:
            %logout
        """

        self.retval = None
        self.kernel.do_logout()

    def line_param(self, variable, value):
        """
        %param VARIABLE VALUE

        Define a hostname/env variable.
        This is useful for parameterized notebook execution using papermill.

        Examples:
            In [1]:
            %param HOST_A 10.10.10.10
            %param HOST_B 11.11.11.11

            In[2]:
            %login {HOST_A}

            In[3]:
            echo $HOST_B

            Out[3]:
            11.11.11.11
        """
        try:
            validate_value_string(value)
            self.kernel.set_param(variable, value)
        except Exception as exc:
            # To propagate exception to frontend through metakernel
            # store ExceptionWrapper instance into retval
            ex_type, _ex, _tb = sys.exc_info()
            tb_format = traceback.format_exc().splitlines()
            self.retval = ExceptionWrapper(ex_type.__name__, repr(exc.args), tb_format)

    def post_process(self, retval):
        try:
            return self.retval
        except AttributeError:
            return retval


def expand_parameters(host, params):
    """Expand parameters in hostname.

    Examples:
    * "target{N}" => "target1"
    * "{host}.{domain} => "host01.example.com"

    """
    pattern = r"\{(.*?)\}"

    def repl(match):
        param_name = match.group(1)
        return params[param_name]

    return re.sub(pattern, repl, host)


blacklist = re.compile(r".*([^- %,\./:=_a-zA-Z\d@])")


def validate_value_string(val_str):
    """Raise if given string contains invalid characters.

    Args:
        val_str (str)

    Raises:
        ValueError: If `val_str` matches `blacklist`
    """
    m = re.match(blacklist, str(val_str))
    if m:
        msg = "{val} contains invalid character {matched}. Valid characters are A-Z a-z 0-9 - % , . / : = _ @".format(
            val=repr(val_str), matched=repr(m.group(1))
        )
        raise ValueError(msg)


def register_magics(kernel):
    kernel.register_magics(SSHKernelMagics)
