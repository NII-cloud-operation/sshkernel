from pssh.clients.native.single import SSHClient
from pssh.clients.native.parallel import ParallelSSHClient

def single():
    c = SSHClient('localhost')
    cmd = '''
    for i in `seq 5`
    do echo $i
    notfound
    sleep 1
    done
    '''
    (channel, host, stdout, stderr, stdin) = c.run_command(cmd)

    for l in stdout:
        print(l)

    for l in stderr:
        print(l)

    # stdin.close()  ## this closes channel before read stdout

def parallel(*, join, use_pty):
    c = ParallelSSHClient(['localhost'])
    cmd = '''
    env
    man man
    for i in `seq 3`
    do
        sleep 1
        notfound
        echo $i
    done
    '''
    alloutput = c.run_command(cmd, use_pty=use_pty)
    out = hostout = alloutput['localhost']

    print(type(hostout))
    print(type(hostout.stdout))

    code = c.get_exit_code(out)
    print("code = {}".format(code))

    for l in out.stdout:
        print(l)
        code = c.get_exit_code(out)
        print("code = {}".format(code))
        print("exit_code() = {}".format(out.exit_code))
        print("exception() = {}".format(out.exception))

    for l in out.stderr:
        print(l)
        code = c.get_exit_code(out)
        print("code = {}".format(code))

    if join:
        c.join(alloutput)

    print("last_output() = {}".format(c.get_last_output()))

    code = c.get_exit_code(hostout)
    print("code = {}".format(code))



def main():
    parallel(join=True, use_pty=True)

main()
