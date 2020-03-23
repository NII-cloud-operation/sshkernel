from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()


version = {}
with open("sshkernel/version.py") as f:
    exec(f.read(), version)
# later on we use: version['__version__']


def _requirements():
    return [name for name in open("requirements.txt").readlines()]


setup(
    name="sshkernel",
    version=version["__version__"],
    author="UENO, Masaru",
    author_email="ueno.masaru@fujitsu.com",
    description="SSH Kernel",
    extras_require={"dev": ["pytest>=3", "pytest-watch"]},
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=_requirements(),
    license='BSD 3-clause "New" or "Revised License"',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nii-cloud-operation/sshkernel",
    packages=["sshkernel"],
    classifiers=[
        "Framework :: IPython",
        "Framework :: Jupyter",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Shells",
    ],
)
