import glob
import os
import unittest

import papermill as pm

from sshkernel.kernel import SSHKernel


class SSHDIntegrationTests(unittest.TestCase):
    def test_proxycommand(self):
        """
        # Expect the config below
        Host localhost
            User root
            Port 22
            IdentityFile {keyfile}
            ProxyCommand ssh -W %h:%p {bastion}
        """
        kernel = SSHKernel()
        kernel.do_login("localhost")
        kernel.assert_connected()

    def list_notebooks(self):
        here = os.path.dirname(__file__)
        nbs = glob.glob("{}/*.ipynb".format(here))

        return nbs

    def test_no_raise(self):

        nbs = self.list_notebooks()

        here = os.path.dirname(__file__)
        out_dir = "{}/out".format(here)
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        for nb_input in nbs:
            basename = os.path.basename(nb_input)

            nb_output = "{}/{}".format(out_dir, basename)

            try:
                pm.execute_notebook(nb_input, nb_output)
            except Exception as e:
                with open(nb_output) as f:
                    print(f.read())

                raise e

        self.assertEqual(1, 1)
