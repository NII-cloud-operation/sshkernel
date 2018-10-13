from Exscript import Account
from Exscript.protocols import SSH2

username = 'temp'
password = 'temp'
debug = 0

session = SSH2(debug=debug)
session.set_driver('shell')
session.connect('localhost')

print('* login...')
session.login(Account(username, password=password))
print('* logged in')

# print all lines
# FIXME: use data_received_event Event()
def print_handler(self, i, match):
    print('remote >' + match.group(0))

# session.add_monitor('.*', print_handler)


def mycallback(*arg):
    print("\n".join(arg))

session.data_received_event.connect(mycallback)

def run(cmd, sess):
    sess.execute(cmd)    

run('id', session)
run('cd /tmp', session)
run('pwd', session)

# 非同期
run('echo running...; sleep 1 ; echo a; sleep 3; echo done', session)

session.client # transport #
session.shell  # channel
session.shell.makefile() # ChannelFile

# SSHセッションの切断
if session:
    session.send('exit\r')
    session.close() # EOFError
