import re
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
        self.kernel.set_param(variable, value)
        self.retval = None

    def expand_parameters(self, string, params):
        pattern = r'\{(.*?)\}'
        def repl(match):
            param_name = match.group(1)
            return params[param_name]

        return re.sub(pattern, repl, string)

    def post_process(self, retval):
        return self.retval


def register_magics(kernel):
    kernel.register_magics(SSHKernelMagics)
