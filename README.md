# Python Module Template gitkv
## Overview

Use a git repo as a key-value store.

## Usage

    import gitkv
    with gitkv.open(repo_url, fname) as f:
        f.write(data)

## Documentation

See http://gitkv.readthedocs.io/

## Installation
GitKV depends on libgit2:

    $ wget https://github.com/libgit2/libgit2/archive/v0.25.0.tar.gz
    $ tar xzf v0.25.0.tar.gz
    $ cd libgit2-0.25.0/
    $ cmake .
    $ make
    $ sudo make install

On a Debian system, make sure you install the following packages first:

    $ apt-get install git
    $ apt-get install libffi6 libffi-dev

To install use pip:

    $ pip3 install gitkv


Or clone the repo:

    $ git clone https://github.com/edouardklein/gitkv.git
    $ python3 setup.py install

Troubleshooting

The verification step may fail if the dynamic linker does not find the libgit2 library: 


     Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/root/Téléchargements/gitkv/gitkv/__init__.py", line 1, in <module>
        from .gitkv import *
      File "/root/Téléchargements/gitkv/gitkv/gitkv.py", line 22, in <module>
        import pygit2
      File "/usr/local/lib/python3.6/site-packages/pygit2-0.25.0-py3.6-linux-x86_64.egg/pygit2/__init__.py", line 32, in <module>
        from _pygit2 import *
    ImportError: libgit2.so.25: cannot open shared object file: No such file or directory

This happens for instance in Ubuntu, the libgit2 library is installed within the /usr/local/lib directory, but the linker does not look for it there. To fix this call ldconfig:

$ sudo ldconfig

