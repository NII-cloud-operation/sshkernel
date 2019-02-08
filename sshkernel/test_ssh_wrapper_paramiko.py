import unittest

@unittest.skip('Replace to SSHWrapperPlumbum')
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

        def cl_exec_command_double(cmd, print_function, **kwargs):
            if not connected:
                raise SSHException
            return 0

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
        self.instance._client = Mock()
        self.instance._client.get_transport = Mock(side_effect=SSHException)

        with self.assertRaises(SSHException):
            self.instance.exec_command('yo', lambda line: None)

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
                set(['username', 'port', 'key_filename'])
            )
