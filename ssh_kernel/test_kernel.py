from textwrap import dedent
from unittest.mock import Mock
from unittest.mock import PropertyMock
import io
import unittest

from .kernel import SSHKernel
from .ssh_wrapper import SSHWrapper
from ipykernel.kernelbase import Kernel
from ssh_kernel import SSHException
from ssh_kernel import ExceptionWrapper


class SSHKernelTest(unittest.TestCase):

    def setUp(self):
        self.instance = SSHKernel()
        type(self.instance).sshwrapper = PropertyMock(return_value=Mock(spec=SSHWrapper))
        self.instance.Error = Mock()
        self.instance.Print = Mock()
        self.instance.Write = Mock()

    def test_new(self):
        self.assertIsInstance(self.instance, Kernel)
        self.assertIsInstance(self.instance, SSHKernel)
        self.assertIsInstance(self.instance.sshwrapper, SSHWrapper)

    def test_property_mock_returns_sshwrapper_mock(self):
        ''' test for mock '''
        self.assertIsInstance(self.instance.sshwrapper, SSHWrapper)

        with self.assertRaises(AttributeError):
            self.instance.sshwrapper.nomethod()

    def test_impl(self):
        self.assertEqual(self.instance.implementation, 'ssh_kernel')

    def test_banner(self):
        self.assertIn('SSH', self.instance.banner)

    def test_do_execute_direct_calls_exec_command(self):
        cmd = 'date'
        cmd_result = "Sat Oct 27 19:45:46 JST 2018\n"
        print_function = Mock()
        self.instance.sshwrapper.exec_command = Mock(return_value=0)

        self.assertEqual(0, self.instance.sshwrapper.exec_command())

        err = self.instance.do_execute_direct(cmd, print_function)

        self.assertIsNone(err)
        self.instance.sshwrapper.exec_command.assert_called()

    def test_exec_with_error_exit_code_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(return_value=1)

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)
        self.assertEqual(err.evalue, '1')

    def test_exec_with_exception_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(side_effect=SSHException("boom"))

        err = self.instance.do_execute_direct('sl')

        self.assertIsInstance(err, ExceptionWrapper)

    def test_exec_with_interrupt_should_return_exception(self):
        self.instance.sshwrapper.exec_command = Mock(side_effect=KeyboardInterrupt())

        err = self.instance.do_execute_direct('sleep 10000')

        self.instance.Write.assert_not_called()

        self.assertIsInstance(err, ExceptionWrapper)
        self.assertEqual(err.ename, 'abort')
        self.assertIsInstance(err.evalue, str)
        self.assertIsInstance(err.traceback, list)

        self.instance.Error.assert_called()

    def test_exec_without_connected_should_return_exception(self):
        self.instance.sshwrapper.isconnected = Mock(return_value=False)
        err = self.instance.do_execute_direct('echo Before connect')

        self.instance.sshwrapper.isconnected.assert_called_once_with()
        self.assertIsInstance(err, ExceptionWrapper)


    def test_restart_kernel_should_call_close(self):
        self.instance.restart_kernel()

        self.instance.sshwrapper.close.assert_called_once_with()


    @unittest.skip("Moving to test_magic.py")
    def test_login_magic(self):
        # magic method call is received
        host = 'dummy'
        (msg, err) = self.instance.Login(host)

        self.assertIsInstance(msg, str)
        self.instance.sshwrapper.connect.assert_called_once_with(host)

    def check_completion(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], 'ok')

        self.assertIn('matches', result)
        matches = result['matches']
        self.assertEqual(matches, sorted(matches))
        self.assertEqual(matches, [e.rstrip() for e in matches])

    def test_complete_bash_variables(self):
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

    def test_complete_bash_commands(self):
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

        self.instance.sshwrapper.exec_command = exec_double

        res = self.instance.do_complete('ls', 3)
        self.check_completion(res)

        self.assertEqual(
            res['matches'],
            ['ls', 'lslogins', 'lspcmcia']
        )
