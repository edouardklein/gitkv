from setuptools import setup, find_packages
from codecs import open
from os import path

__version__ = '1.0.0'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


install_requires = ['sphinx', 'flake8', 'coverage']
dependency_links = []

setup(
    name='gitkv',
    version=__version__,
    description='Use a git repo as a key-value store.',
    long_description=long_description,
    url='https://github.com/edouardklein/gitkv',
    download_url='https://github.com/edouardklein/gitkv/tarball/' + __version__,
    license='AGPLv3',
    classifiers=[
	'Programming Language :: Python :: 3.4',
    ],
    keywords='gitkv use a git repo as a key-value store.',
    packages=['gitkv'],
    include_package_data=True,
    author='HaiLuan Nguyen, Edouard Klein',
    install_requires=install_requires,
    dependency_links=dependency_links,
    author_email='edouardklein@gmailnospam.com'
)
