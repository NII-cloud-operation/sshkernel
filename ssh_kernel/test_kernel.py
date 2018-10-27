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
import paramiko


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
        closed = True
        connected = False

        client_double = Mock(spec=SSHWrapper)
        chan_double = Mock(spec=paramiko.BufferedFile)

        def readline_double(cmd: str):
            if closed:
                raise IOError("File is closed")
            return (io.BytesIO(), io.StringIO('yo'), io.BytesIO())

        def read_double():
            if closed:
                raise IOError("File is closed")
            return (
                io.BytesIO(),
                io.BytesIO(bytes('yo', 'utf-8')),
                io.BytesIO(),
            )

        def cl_exec_command_double(cmd, **kwargs):
            if not connected:
                raise paramiko.SSHException
            return (chan_double(), chan_double(), chan_double())

        def cl_connect(host):
            connected = True

        chan_double.read = MagicMock(side_effect=read_double)
        chan_double.readline = MagicMock(side_effect=readline_double)
        client_double.exec_command = MagicMock(side_effect=cl_exec_command_double)
        client_double.connect = MagicMock(side_effect=cl_connect)

        instance = SSHWrapperParamiko()
        instance._client = client_double

        self.instance = instance

    def test_connect_should_call_paramiko_connect(self):
        mock = MagicMock()

        #
        # connect()中にparamiko.SSHClient()をnewするのでそのコンストラクタを差し替える
        #
        _client = paramiko.SSHClient()
        _client.connect = mock
        self.instance._new_paramiko_client = lambda: _client  # FIXME: self?

        self.instance.connect("dummy")

        mock.assert_called_once_with("dummy")  # 送信のテスト


    def test_exec_command_returns_error_at_first(self):
        with self.assertRaises(paramiko.SSHException):
            self.instance.exec_command('yo')

    @unittest.skip("fixing connect")
    def test_exec_command_returns_stream(self):
        self.instance.connect('myserver')
        ret = self.instance.exec_command('yo')

        for meth in ['read', 'readline', 'readlines']:
            self.assertIn(meth, dir(ret))

    def test_close_should_delegate(self):
        mock = MagicMock()
        self.instance._client.close = mock
        self.instance.close()

        mock.assert_called_once()

    def test_init_ssh_config(self):
        import tempfile
        from textwrap import dedent
        with tempfile.NamedTemporaryFile('w') as f:
            f.write(dedent("""
            Host test
                HostName 127.0.0.10
                User testuser
                IdentityFile ~/.ssh/id_rsa_test
            """))

            f.seek(0)

            (hostname, lookup) = self.instance._init_ssh_config(f.name, "test")

            self.assertIsInstance(lookup, dict)
            self.assertEqual(hostname, "127.0.0.10")
