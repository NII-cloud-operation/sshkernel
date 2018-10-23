from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import Mock
from unittest.mock import patch
import io
import unittest

from .kernel import SSHKernel
from .kernel import SSHWrapper
from .kernel import SSHWrapperParamiko
from ipykernel.kernelbase import Kernel


class SSHKernelTest(unittest.TestCase):

    def setUp(self):
        if not hasattr(self, 'instance'):
            self.instance = SSHKernel()
        self.wrapper = Mock(spec=SSHWrapper)

    def test_new(self):
        self.assertIsInstance(self.instance, Kernel)
        self.assertIsInstance(self.instance, SSHKernel)

    def test_impl(self):
        self.assertEqual(self.instance.implementation, 'ssh_kernel')

    def test_process_output(self):
        instance = SSHKernel()
        instance.sshwrapper = self.wrapper

        instance.silent = False
        for cmd in ["hello", "world"]:
            with self.subTest(cmd=cmd):
                instance.send_response = Mock()

                stream = io.StringIO("hello world")
                instance.process_output(stream)

                instance.send_response.assert_called_once()


class SSHWrapperParamikoTest(unittest.TestCase):

    def setUp(self):
        self.instance = SSHWrapperParamiko()

    def test_exec_command_returns_error_at_first(self):
        self.instance.exec_command('yo')

    def test_exec_command_returns_stream(self):
        self.instance._client = 0
        self.instance.exec_command('yo')


