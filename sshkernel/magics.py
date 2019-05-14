import re
import sys
import traceback

from metakernel import ExceptionWrapper
from metakernel import Magic


class SSHKernelMagics(Magic):

    blacklist = re.compile(r'.*([^- %,\./:=_a-zA-Z\d@])')

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
        self.kernel.new_ssh_wrapper()
        self.kernel.Print('[ssh] Login to {}...'.format(host))

        try:
            host = self.expand_parameters(host, self.kernel.get_params())
            self.kernel.sshwrapper.connect(host)
        except Exception as e:
            self.kernel.Error("[ssh] Login to {} failed.".format(host))

            tb = traceback.format_exc().splitlines()

            # (name, value, tb)
            self.retval = ExceptionWrapper('SSHConnectionError', 'Login to {} failed.'.format(host), tb)
        else:
            self.kernel.Print('[ssh] Successfully logged in.')

    def line_logout(self):
        '''
        %logout

        Logout and disconnect.

        Example:
            %logout
        '''

        self.retval = None

        # TODO: Using self.kernel is awkward

        # TODO: Error handling
        self.kernel.sshwrapper.close()
        self.kernel.Print('[ssh] Successfully logged out.')

    def line_param(self, variable, value):
        '''
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
        '''
        try:
            self.validate_value_string(value)
            self.kernel.set_param(variable, value)
        except Exception as exc:
            # To propagate exception to frontend through metakernel
            # store ExceptionWrapper instance into retval
            ex_type, _ex, _tb = sys.exc_info()
            tb_format = traceback.format_exc().splitlines()
            self.retval = ExceptionWrapper(ex_type.__name__, repr(exc.args), tb_format)

    def expand_parameters(self, string, params):
        pattern = r'\{(.*?)\}'

        def repl(match):
            param_name = match.group(1)
            return params[param_name]

        return re.sub(pattern, repl, string)

    def validate_value_string(self, val_str):
        '''Raise if given string contains invalid characters.

        Args:
            val_str (str)

        Raises:
            ValueError: If `val_str` matches `self.blacklist`
        '''
        m = re.match(self.blacklist, str(val_str))
        if m:
            msg = "{val} contains invalid character {matched}. Valid characters are A-Z a-z 0-9 - % , . / : = _ @".format(
                val=repr(val_str), matched=repr(m.group(1))
            )
            raise ValueError(msg)

    def post_process(self, retval):
        try:
            return self.retval
        except AttributeError:
            return retval

def register_magics(kernel):
    kernel.register_magics(SSHKernelMagics)
