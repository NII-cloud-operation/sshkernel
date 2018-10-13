from fabric import Connection


c = Connection('localhost', user='temp', connect_kwargs=dict(password='temp'))

c.run('id', pty=True)
c.run('cd /tmp', pty=True)
c.run('ls', pty=True)
c.run('echo $0', pty=True)

c.run('ssh localhost', pty=True)

r = c.run('echo "\n> "; a=read; echo $a')

print(r.stdout)