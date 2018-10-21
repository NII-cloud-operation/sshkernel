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

        print("** login **")
        self.kernel.Login(host)


def register_magics(kernel):
    kernel.register_magics(LoginMagic)
