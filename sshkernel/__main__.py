from ipykernel.kernelapp import IPKernelApp
from .kernel import SSHKernel
IPKernelApp.launch_instance(kernel_class=SSHKernel)
