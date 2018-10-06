import base64
import select
import sys

import paramiko
from paramiko.py3compat import u

from IPython import embed


class ClientManager():
    def __init__(self):
        self.new()

    def new(self):
        client = paramiko.SSHClient()
    #    client.get_host_keys().add('ssh.example.com', 'ssh-rsa', key)
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.WarningPolicy())

        client.connect('localhost')

        self.client = client

    def ls(self):
        client = self.client

        # "session" is a type of Channel

        # Channel is an abstraction for SSH2 channel
        # like a socket
        t = client.get_transport()
        ch = client.get_transport().open_session()
        pty = ch.get_pty()      # This is usually used right after creating a client channel
        sh = ch.invoke_shell()  # Normally you would call get_pty before this

        #embed()

        stdin, stdout, stderr = client.exec_command(
            'date; echo sleep 3...; sleep 3; ls')

        print(client.get_transport())

        for line in stdout:
            print('paramiko> ' + line.strip('\n'))

    def ls2(self):
        client = self.client

        def handler(ch):
            while True:
                i, o, e = select.select([ch], [], [])

                x = u(ch.recv(1024))
                if len(x) == 0:
                    sys.stdout.write("\n*** EOF\n")
                    break

                #print(s)
                sys.stdout.write(x)

        # Start an interactive shell session on the SSH server
        chan = client.invoke_shell()

        # go func
        (lambda ch: handler(ch))(chan)

        chan.send("ls; sleep 3")
        chan.send("ls")



    def close(self):
        client = self.client

        print("Closing {}", client)
        client.close()


def main():
    cm = ClientManager()
    try:
        cm.ls()
        cm.ls()
    finally:
        cm.close()


main()
