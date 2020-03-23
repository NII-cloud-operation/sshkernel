import unittest
from unittest.mock import Mock

from sshkernel.kernel import SSHKernel
from sshkernel.magics.magics import SSHKernelMagics
from sshkernel.magics.magics import expand_parameters
from sshkernel.magics.magics import validate_value_string

from paramiko import AuthenticationException


class MagicTest(unittest.TestCase):
    def setUp(self):
        kernel = Mock(spec=SSHKernel)
        instance = SSHKernelMagics(kernel=kernel)
        self.kernel = kernel
        self.instance = instance

    def test_login_should_call_do_login(self):
        host = "dummy"
        self.instance.line_login(host)

        self.kernel.do_login.assert_called_once_with(host)
        self.assertIsNone(self.instance.retval)

    def test_logout_should_call_logout(self):
        self.instance.line_logout()

        self.kernel.do_logout.assert_called_once_with()

    def test_login_with_exception_set_retval(self):
        self.kernel.do_login = Mock(side_effect=AuthenticationException)

        self.instance.line_login("dummy")
        self.assertIsNotNone(self.instance.retval)

    def test_expand_parameters(self):
        params = dict(A="1", B="3")
        s = "{A}2{B}"

        ret = expand_parameters(s, params)
        self.assertEqual(ret, "123")

    def test_expand_parameters_raise(self):
        with self.assertRaises(KeyError):
            expand_parameters("{NOTFOUND}", {})

    def test_expand_parameters_with_unclosed_string(self):
        ret = expand_parameters("{YO", {})
        self.assertEqual(ret, "{YO")

    def test_validate_value_string(self):
        func = validate_value_string

        ok_cases = [
            "abc 123%@-",
        ]
        ng_cases = [
            "ABC ###",
            'ABC"',
            "ABC()",
            "ABC${}",
        ]

        for ok in ok_cases:
            self.assertIsNone(func(ok))

        for ng in ng_cases:
            with self.assertRaises(ValueError):
                func(ng)
