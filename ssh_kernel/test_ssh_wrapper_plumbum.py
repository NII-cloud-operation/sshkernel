from textwrap import dedent
from unittest.mock import Mock
from unittest.mock import PropertyMock
import io
import socket
import unittest

import paramiko
from plumbum.machines.paramiko_machine import ParamikoMachine

from .ssh_wrapper import SSHWrapper
from .ssh_wrapper_plumbum import SSHWrapperPlumbum
from ssh_kernel import ExceptionWrapper
from ssh_kernel import SSHException

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

    @unittest.skip('fix setUp')
    def test_exec_command_returns_error_at_first(self):
        with self.assertRaises(socket.gaierror):
            self.instance.exec_command('yo', lambda line: None)

    @unittest.skip("fixing connect")
    def test_exec_command_returns_stream(self):
        self.instance.connect('myserver')
        ret = self.instance.exec_command('yo')

        for meth in ['read', 'readline', 'readlines']:
            self.assertIn(meth, dir(ret))

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
