import asyncio
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

        client.connect('localhost', username="temp", password="temp", timeout=1)

        self.client = client

    async def handler(self, buf):
        for l in buf:
            sys.stdout.write('paramiko> ' + l)

    def ls2(self):
        client = self.client

        _, o, e = client.exec_command("ls -l; sleep 2; echo done")

        # go func
        # (lambda s: self.handler(s))(o)
        # (lambda s: self.handler(s))(e)
        h = self.handler(o)

        print("* returning ls2")

        return h

    def uptime(self):
        # loop = asyncio.get_event_loop()
        _, o, e = self.client.exec_command('uptime; sleep 2; echo done')
        # return loop.run_in_executor(None, self.handler, o)

        print("sent")

        return self.handler(o)


    def close(self):
        client = self.client

        print("Closing {}", client)
        client.close()


async def _main():
    cm = ClientManager()
    try:
        # いやいや、順に実行してほしいよ
        # queueing?
        # sequenceかくか
        futures = [
            cm.uptime(),
            cm.uptime(),
        ]

        print(futures)

        return asyncio.gather(*futures)

    finally:
        #cm.close()
        pass

def main():
    loop = asyncio.get_event_loop()
    # Blocking call which returns when the hello_world() coroutine is done
    loop.run_until_complete(_main())
    loop.close()

main()
