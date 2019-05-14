from abc import ABC, abstractmethod 

class SSHWrapper(ABC):
    @abstractmethod
    def __init__(self, envdelta):
        '''
        Args:
            envdelta (dict) envdelta is injected into remote environment variables
        '''

    @abstractmethod
    def exec_command(self, cmd, print_function):
        '''
        Args:
            cmd (string)
            print_function (lambda)

        Returns:
            int: exit code
        '''

    @abstractmethod
    def connect(self, host):
        '''
        Connect to host

        Raises:
            SSHConnectionError
        '''

    @abstractmethod
    def close(self):
        '''
        Close connection to host
        '''

    @abstractmethod
    def interrupt(self):
        '''
        Send SIGINT to halt current execution
        '''

    @abstractmethod
    def isconnected(self):
        '''
        Connected to host or not

        Returns:
            bool
        '''
