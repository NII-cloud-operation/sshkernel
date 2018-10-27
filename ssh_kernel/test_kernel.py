from unittest.mock import Mock
import io
import unittest

from .kernel import SSHKernel
from .kernel import SSHWrapper
from .kernel import SSHWrapperParamiko
from ipykernel.kernelbase import Kernel
import paramiko
from ssh_kernel import SSHException
from ssh_kernel import ExceptionWrapper


class SSHKernelTest(unittest.TestCase):

    def setUp(self):
        self.instance = SSHKernel()
        self.instance.sshwrapper = Mock(spec=SSHWrapper)
        self.instance.Error = Mock()
        self.instance.Print = Mock()
        self.instance.Write = Mock()

    def test_new(self):
        self.assertIsInstance(self.instance, Kernel)
        self.assertIsInstance(self.instance, SSHKernel)
        self.assertIsInstance(self.instance.sshwrapper, SSHWrapper)

    def test_impl(self):
        self.assertEqual(self.instance.implementation, 'ssh_kernel')

    def test_process_output(self):
        instance = self.instance

        instance.silent = False
        for cmd in ["hello", "world"]:
            with self.subTest(cmd=cmd):
                mock = Mock()
                instance.Write = mock

                stream = io.StringIO("hello world")
                instance.process_output(stream)

                mock.assert_called_once()

    def test_process_output_with_silent(self):
        self.instance.silent = True

        self.instance.process_output("hello")

        self.instance.Write.assert_not_called()

    def test_banner(self):
        self.assertIn('SSH', self.instance.banner)

    def test_do_execute_direct_calls_exec_command(self):
        cmd = 'date'
        cmd_result = "Sat Oct 27 19:45:46 JST 2018\n"
        self.instance.sshwrapper.exec_command = Mock(return_value=io.StringIO(cmd_result))
        self.instance.do_execute_direct(cmd)

        self.instance.sshwrapper.exec_command.assert_called_once_with(cmd)
        self.instance.sshwrapper.exit_code.assert_called_once_with()
        self.instance.Write.assert_called_once_with(cmd_result)

    def test_exec_with_error_exit_code_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(return_value=io.StringIO("bash: sl: command not found\n"))
        self.instance.sshwrapper.exit_code = Mock(return_value=1)

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)

    def test_exec_with_exception_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(side_effect=SSHException("boom"))

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)

    def test_exec_with_interrupt_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(side_effect=KeyboardInterrupt())

        err = self.instance.do_execute_direct('sleep 10000')

        self.instance.Write.assert_not_called()

        self.assertIsInstance(err, ExceptionWrapper)
        self.instance.Error.assert_called_once()

    def test_restart_kernel_should_call_close(self):
        self.instance.restart_kernel()

        self.instance.sshwrapper.close.assert_called_once_with()

    def test_login_magic(self):
        # magic method call is received
        host = 'dummy'
        (msg, err) = self.instance.Login(host)

        self.assertIsInstance(msg, str)
        self.instance.sshwrapper.connect.assert_called_once_with(host)


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
                raise SSHException
            return (chan_double(), chan_double(), chan_double())

        def cl_connect(host):
            connected = True

        chan_double.read = Mock(side_effect=read_double)
        chan_double.readline = Mock(side_effect=readline_double)
        client_double.exec_command = Mock(side_effect=cl_exec_command_double)
        client_double.connect = Mock(side_effect=cl_connect)

        instance = SSHWrapperParamiko()
        instance._client = client_double

        self.instance = instance

    def test_connect_should_call_paramiko_connect(self):
        mock = Mock()

        #
        # connect()中にparamiko.SSHClient()をnewするのでそのコンストラクタを差し替える
        #
        _client = paramiko.SSHClient()
        _client.connect = mock
        self.instance._new_paramiko_client = lambda: _client  # FIXME: self?

        self.instance.connect("dummy")

        mock.assert_called_once_with("dummy")  # 送信のテスト


    def test_exec_command_returns_error_at_first(self):
        with self.assertRaises(SSHException):
            self.instance.exec_command('yo')

    @unittest.skip("fixing connect")
    def test_exec_command_returns_stream(self):
        self.instance.connect('myserver')
        ret = self.instance.exec_command('yo')

        for meth in ['read', 'readline', 'readlines']:
            self.assertIn(meth, dir(ret))

    def test_close_should_delegate(self):
        mock = Mock()
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

        with tempfile.NamedTemporaryFile('w') as f:
            f.write(dedent("""
            Host test2
                IdentityFile ~/.ssh/id_rsa_test
            """))

            f.seek(0)

            (hostname, lookup) = self.instance._init_ssh_config(f.name, "test2")

            self.assertIsInstance(lookup, dict)
            self.assertEqual(hostname, "test2")