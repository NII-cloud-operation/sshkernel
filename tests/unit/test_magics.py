from unittest.mock import Mock
import io
import unittest

from metakernel import Magic

from sshkernel import ExceptionWrapper
from sshkernel import SSHException
from sshkernel.kernel import SSHKernel
from sshkernel.magics import SSHKernelMagics


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

    def test_login_without_host_raise_type_exception(self):
        with self.assertRaises(TypeError):
            self.instance.line_login()

    def test_login_set_retval_none(self):
        noreturn = self.instance.line_login('dummy')

        self.assertIsNone(noreturn)
        self.assertIsNone(self.instance.retval)
