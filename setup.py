from setuptools import setup
import re


with open("README.md", "r") as fh:
    long_description = fh.read()


with open('sshkernel/__init__.py', 'rt', encoding='utf8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


def _requirements():
    return [name for name in open('requirements.txt').readlines()]


setup(
    name="sshkernel",
    version=version,
    author="UENO, Masaru",
    author_email="ueno.masaru@fujitsu.com",
    description="SSH Kernel",
    extras_require={
        'dev': [
            'coverage',
            'pytest>=3',
            'pytest-watch',
            'tox',
            'twine',
            'wheel',
        ],
    },
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=_requirements(),
    license='BSD 3-clause "New" or "Revised License"',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=['sshkernel'],
    classifiers=[
        "Framework :: IPython",
        "Framework :: Jupyter",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Shells",
    ],
)
