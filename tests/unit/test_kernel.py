from textwrap import dedent
from unittest.mock import Mock
from unittest.mock import PropertyMock
from unittest.mock import patch
import io
import unittest

from ipykernel.kernelbase import Kernel
from sshkernel import ExceptionWrapper
from sshkernel import SSHException
from sshkernel.exception import SSHKernelNotConnectedException
from sshkernel.kernel import SSHKernel
from sshkernel.ssh_wrapper import SSHWrapper


class SSHKernelTest(unittest.TestCase):

    def setUp(self):
        self.instance = SSHKernel()
        # type(self.instance).sshwrapper = PropertyMock(return_value=Mock(spec=SSHWrapper))
        self.instance.Error = Mock()
        self.instance.Print = Mock()
        self.instance.Write = Mock()

    def test_new(self):
        self.assertIsInstance(self.instance, Kernel)
        self.assertIsInstance(self.instance, SSHKernel)
        self.assertIsNone(self.instance.sshwrapper)

    def test_impl(self):
        self.assertEqual(self.instance.implementation, 'sshkernel')

    def test_banner(self):
        self.assertIn('SSH', self.instance.banner)

    def test_do_execute_direct_calls_exec_command(self):
        cmd = 'date'
        cmd_result = "Sat Oct 27 19:45:46 JST 2018\n"
        print_function = Mock()

        with patch('sshkernel.kernel.SSHKernel.sshwrapper', new_callable=PropertyMock) as wrapper_double:
    #       type(self.instance).sshwrapper = Mock()
    #        self.instance.new_ssh_wrapper()
            self.instance.sshwrapper.exec_command = Mock(return_value=0)

            self.assertEqual(0, self.instance.sshwrapper.exec_command())

            err = self.instance.do_execute_direct(cmd, print_function)

            self.assertIsNone(err)
            self.instance.sshwrapper.exec_command.assert_called()

    def test_exec_with_error_exit_code_should_return_exception(self):
        self.instance.new_ssh_wrapper()
        self.instance.assert_connected = Mock()
        self.instance.sshwrapper.exec_command = Mock(return_value=1)

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)
        self.assertEqual(err.evalue, '1')

    def test_exec_with_exception_should_return_exception(self):
        self.instance.new_ssh_wrapper()
        self.instance.sshwrapper.exec_command = Mock(side_effect=SSHException("boom"))

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)

    def test_exec_with_interrupt_should_return_exception(self):
        self.instance.new_ssh_wrapper()
        self.instance.sshwrapper.exec_command = Mock(side_effect=KeyboardInterrupt())

        err = self.instance.do_execute_direct('sleep 10000')

        self.instance.Write.assert_not_called()

        self.assertIsInstance(err, ExceptionWrapper)
        self.assertEqual(err.ename, 'abort')
        self.assertIsInstance(err.evalue, str)
        self.assertIsInstance(err.traceback, list)

        self.instance.Error.assert_called()

    def test_exec_without_connected_should_return_exception(self):
        self.instance.new_ssh_wrapper()
        self.instance.sshwrapper.isconnected = Mock(return_value=False)
        err = self.instance.do_execute_direct('echo Before connect')

        self.instance.sshwrapper.isconnected.assert_called_once_with()
        self.assertIsInstance(err, ExceptionWrapper)

    @patch('sshkernel.kernel.SSHKernel.sshwrapper', new_callable=PropertyMock)
    def test_restart_kernel_should_call_close(self, prop):
        wrapper_double = Mock()
        prop.return_value = wrapper_double

        self.instance.restart_kernel()

        wrapper_double.close.assert_called_once()

    @unittest.skip("Moving to test_magic.py")
    def test_login_magic(self):
        # magic method call is received
        host = 'dummy'
        (msg, err) = self.instance.Login(host)

        self.assertIsInstance(msg, str)
        self.instance.sshwrapper.connect.assert_called_once_with(host)

    def test_get_completions_should_return_empty_array_not_connected(self):
        connected_double = Mock(side_effect=SSHKernelNotConnectedException)

        self.instance.assert_connected = connected_double
        info = dict(
            line='',
            column=0,
        )

        matches = self.instance.get_completions(info)

        connected_double.assert_called_once()
        self.assertEqual(matches, [])

    def test_get_completions_should_return_empty_array_with_empty_string(self):
        for line in ['', 'trailingspace ', ';  ;;']:
            connected_double = Mock(return_value=True)
            self.instance.assert_connected = connected_double
            info = dict(
                line=line,
                column=len(line),
            )

            matches = self.instance.get_completions(info)

            connected_double.assert_called_once()
            self.assertEqual(matches, [])

    def check_completion(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'ok')

        self.assertIn('matches', result)
        matches = result['matches']
        self.assertEqual(matches, sorted(matches))
        self.assertEqual(matches, [e.rstrip() for e in matches])

    @patch('sshkernel.kernel.SSHKernel.sshwrapper', new_callable=PropertyMock)
    def test_complete_bash_variables(self, mock):
        def exec_double(cmd, callback):
            result = dedent(
                """\
                BASH_ARGC
                BASH_ARGV
                BASH_LINENO
                BASH_REMATCH
                """)
            for line in result.split():
                callback(line)

            return 0

        # Replace with double without Mock()
        self.instance.sshwrapper.exec_command = exec_double

        res = self.instance.do_complete('$BASH', 5)

        self.check_completion(res)

        self.assertEqual(
            res['matches'],
            ['$BASH_ARGC', '$BASH_ARGV', '$BASH_LINENO', '$BASH_REMATCH']
        )

    @patch('sshkernel.kernel.SSHKernel.sshwrapper', new_callable=PropertyMock)
    def test_complete_bash_commands(self, mock):
        def exec_double(cmd, callback):
            result = dedent(
                """\
                ls
                ls
                lspcmcia
                lslogins
                """)
            for line in result.split():
                callback(line)
            return 0

        # Replace with double without Mock()
        self.instance.sshwrapper.exec_command = exec_double

        res = self.instance.do_complete('ls', 3)
        self.check_completion(res)

        self.assertEqual(
            res['matches'],
            ['ls', 'lslogins', 'lspcmcia']
        )

    def test_sshwrapper_setter(self):
        self.assertIsNone(self.instance.sshwrapper)
        self.assertIsNone(self.instance._sshwrapper)

        self.instance.sshwrapper = 42

        self.assertEqual(self.instance._sshwrapper, 42)

    def test_new_ssh_wrapper(self):
        # Intanciate outside setUp()
        kernel = SSHKernel()
        kernel.Write = Mock()

        self.assertIsNone(kernel.sshwrapper)
        self.assertIsNone(kernel._sshwrapper)

        kernel.new_ssh_wrapper()

        self.assertIsNotNone(kernel._sshwrapper)
        self.assertIsInstance(kernel._sshwrapper, SSHWrapper)

    @patch('sshkernel.kernel.SSHKernel.sshwrapper', new_callable=PropertyMock)
    def test_new_ssh_wrapper_call_close_if_old_instance_exist(self, prop):
        wrapper_double = Mock()
        prop.return_value = wrapper_double

        self.instance.new_ssh_wrapper()

        wrapper_double.close.assert_called_once()
