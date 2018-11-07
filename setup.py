from setuptools import setup
import re


with open("README.md", "r") as fh:
    long_description = fh.read()


with open('ssh_kernel/__init__.py', 'rt', encoding='utf8') as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


def _requirements():
    return [name.rstrip() for name in open('requirements.txt').readlines()]


setup(
    name="ssh_kernel",
    version=version,
    author="UENO, Masaru",
    author_email="m-ueno@users.noreply.github.com",
    description="SSH Kernel",
    extras_require={
        'dev': [
            'pytest>=3',
            'coverage',
            'tox',
        ],
    },
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=_requirements(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=['ssh_kernel'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Framework :: IPython",
        "Topic :: System :: Shells",
        "License :: OSI Approved :: MIT License",
    ],
)
