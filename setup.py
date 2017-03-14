from setuptools import setup, find_packages
from codecs import open
from os import path

__version__ = '0.0.1'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


install_requires = ['sphinx', 'doctest', 'flake8', 'pygit2']  # FIXME: Explicit requirements here
dependency_links = []  # FIXME: For packages not in pypi http://python-packaging.readthedocs.io/en/latest/dependencies.html#packages-not-on-pypi

with open(path.join(here, 'LICENSE'), encoding='utf-8') as f:
    license_text = f.read()

setup(
    name='gitkv',
    version=__version__,
    description='Use a git repo as a key-value store.',
    long_description=long_description,
    url='https://github.com/edouardklein/gitkv',
    download_url='https://github.com/edouardklein/gitkv/tarball/' + __version__,
    license=license_text,
    classifiers=[
    ],
    keywords='gitkv',
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Edouard Klein',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='edouardklein -at- gmail.com'
)
