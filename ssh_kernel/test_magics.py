from unittest.mock import Mock
import io
import unittest

from metakernel import Magic

from .magics import SSHKernelMagics
from .kernel import SSHKernel
from .kernel import SSHWrapper
from ssh_kernel import SSHException
from ssh_kernel import ExceptionWrapper


class MagicTest(unittest.TestCase):

    def setUp(self):
        kernel = Mock(spec=SSHKernel)
        instance = SSHKernelMagics(kernel=kernel)
        self.kernel = kernel
        self.instance = instance

    def test_login_should_call_connect(self):
        host = "dummy"
        self.instance.line_login(host)

        self.kernel.sshwrapper.connect.assert_called_once_with(host)

    def test_logout_should_call_close(self):
        self.instance.line_logout()

        self.kernel.sshwrapper.close.assert_called_once_with()
