from metakernel import Magic


class LoginMagic(Magic):

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


def register_magics(kernel):
    kernel.register_magics(LoginMagic)
