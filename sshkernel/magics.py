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

    def post_process(self, retval):
        return self.retval


def register_magics(kernel):
    kernel.register_magics(SSHKernelMagics)
