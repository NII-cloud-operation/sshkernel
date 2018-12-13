from textwrap import dedent
from unittest.mock import Mock
from unittest.mock import PropertyMock
from unittest.mock import patch
import io
import socket
import unittest

import paramiko
import plumbum
from plumbum.machines.paramiko_machine import ParamikoMachine

from .ssh_wrapper import SSHWrapper
from ssh_kernel import ExceptionWrapper
from ssh_kernel import SSHException
from ssh_kernel.ssh_wrapper_plumbum import SSHWrapperPlumbum

class SSHWrapperPlumbumTest(unittest.TestCase):

    def setUp(self):
        closed = True
        connected = False

        subscriptable = Mock()
        subscriptable.popen = Mock(return_value=subscriptable)
        subscriptable.__getitem__ = Mock(return_value=subscriptable)
        subscriptable.iter_lines = Mock(return_value=([('output', None), (None, 'err')]))

        remote_double = Mock(spec=ParamikoMachine)
        remote_double.__getitem__ = Mock(return_value=subscriptable)

        instance = SSHWrapperPlumbum()
        instance._remote = remote_double

        self.instance = instance

    def test_connect_should_raise_socket_error(self):
        self.instance._init_ssh_config = Mock(return_value=('dummy', {}))

        # FIXME: fix setUp() to pass the line below
        #self.assertIsNone(self.instance._remote)
        self.assertFalse(self.instance._connected)

        with self.assertRaises(socket.gaierror):
            self.instance.connect("dummy")

    def test_connect_updates_attributes(self):
        remote_double = Mock()
        self.instance._build_remote = Mock(return_value=remote_double)
        dummy = 'dummy'
        #self.assertIsNone(self.instance._remote)
        self.assertFalse(self.instance._connected)
        self.assertEqual(self.instance._host, '')

        self.instance.connect(dummy)

        self.assertTrue(self.instance._connected)
        self.assertEqual(self.instance._host, dummy)
        remote_double.env.update.assert_called()

    @unittest.skip('fix setUp')
    def test_exec_command_returns_error_at_first(self):
        print_mock = Mock()
        with self.assertRaises(socket.gaierror):
            self.instance.exec_command('yo', lambda line: None)

    @unittest.skip
    def test_exec_command_returns_stream(self):
        self.instance.connect('myserver')
        print_mock = Mock()

        ret = self.instance.exec_command('yo', print_mock)

    def test_exec_command_return_exit_code(self):
        print_mock = Mock()

        code = self.instance.exec_command('ls', print_mock)

        self.assertIsInstance(code, int)

    def test_close_should_delegate(self):
        mock = Mock()
        self.instance._remote.close = mock
        self.instance.close()

        mock.assert_called_once()

    def test_init_ssh_config(self):
        import tempfile
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

        with tempfile.NamedTemporaryFile('w') as f:
            f.write(dedent("""
            ForwardAgent yes  ## Cannot handle

            Host test3
                User admin
                Port 2222
                HostName 1.2.3.4
                IdentityFile ~/.ssh/id_rsa_test
            """))

            f.seek(0)

            (hostname, lookup) = self.instance._init_ssh_config(f.name, "test3")

            self.assertEqual(
                set(lookup.keys()),
                set(['user', 'port', 'keyfile'])
            )

    def test_append_command(self):
        cmd = '''
ls
ls
yo
'''
        marker = 'THISISMARKER'

        full_command = self.instance._append_command(cmd, marker)

        self.assertIsInstance(full_command, str)
        self.assertEqual(full_command.count(marker), 3)

    @unittest.skip('Fail to patch plumbum')
    @patch('ssh_kernel.ssh_wrapper_plumbum.SSHWrapperPlumbum.get_cwd', return_value='/tmp')
    @patch('plumbum.machines.paramiko_machine.ParamikoMachine.cwd.getpath._path', return_value='/home')
    def test_update_workdir(self, mock1, mock2):
        mock = Mock()#return_value='/')
        self.instance.get_cwd = mock
        self.instance._remote = mock
        newdir = '/some/where'

        self.instance.update_workdir(newdir)

        mock.assert_called_once()

    @unittest.skip('Fail to patch the instance created in setUp()')
    def test_post_exec(self, env_mock):
        self.instance._remote.env = env_mock
        env_out = '''code: 255
env: A=1^@B=2^@TOKEN=AAAA9B==
pwd: /some/where
'''

        code = self.instance.post_exec_command(env_out)
        self.assertEqual(255, code)

    @patch('ssh_kernel.ssh_wrapper_plumbum.SSHWrapperPlumbum')
    def test__update_interrupt_function(self, proc):
        fn_before = self.instance.interrupt_function
        self.instance._update_interrupt_function(proc)
        fn_after = self.instance.interrupt_function

        self.assertTrue(callable(fn_before))
        self.assertTrue(callable(fn_after))
        self.assertNotEqual(fn_before, fn_after)

    @patch('ssh_kernel.ssh_wrapper_plumbum.SSHWrapperPlumbum')
    def test__update_interrupt_function_inject_proc_to_closure(self, proc):
        self.instance._update_interrupt_function(proc)
        fn_after = self.instance.interrupt_function

        proc.close.assert_not_called()
        fn_after()
        proc.close.assert_called_once()
