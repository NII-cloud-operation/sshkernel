from metakernel import Magic


class SSHKernelMagics(Magic):

    def line_login(self, host):
        """
        %login HOST

        SSH login to the remote host.
        Cells below this line will be executed remotely.

        Example:
            %login localhost
        """

        self.kernel.Print('[ssh] Login to {}...'.format(host))
        try:
            msg, err = self.kernel.Login(host)
            if err:
                self.kernel.Error("[ssh] Login failed: {}".format(msg))
                return
            self.kernel.Print('[ssh] {}'.format(msg))
        except Exception as e:
            # FIXME: Don't handle all exception
            self.kernel.Error(str(e))

    def line_logout(self):
        '''
        %logout

        Logout and disconnect.

        Example:
            %logout
        '''

        # TODO: Using self.kernel is awkward

        # TODO: Error handling
        self.kernel.sshwrapper.close()
        self.kernel.Print('[ssh] Successfully logged out.')


def register_magics(kernel):
    kernel.register_magics(SSHKernelMagics)
