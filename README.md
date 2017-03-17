# Python Module Template gitkv
#FIXME    
- Register your project on ReadTheDocs
- Register your project on PyPI

## Overview

Use a git repo as a key-value store.

## Installation
Install libgit2 :
    $ wget https://github.com/libgit2/libgit2/archive/v0.25.0.tar.gz
    $ tar xzf v0.25.0.tar.gz
    $ cd libgit2-0.25.0/
    $ cmake .
    $ make
    $ sudo make install

apt-get  needed before installation :
    $ apt-get install git
    $ apt-get install libffi6 libffi-dev

To install use pip:

    $ pip3 install gitkv


Or clone the repo:

    $ git clone https://github.com/edouardklein/gitkv.git
    $ python3 setup.py install

verify it is correctly installed:
    
    $ pip install pygit2

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

## Usage

import gitkv
with gitkv.Repo(url) as repo :
	...

### Documentation

Read the documentation gitkv(doc url) to understand how to use gitkv.

### In the cloned repo

#### Helper targets

To build the documentation, run:

    $ make doc
    
To run the test, run:

    $ make test

To check the code's superficial cleanliness run:

    $ make lint
    
To run tests each time a Python file is edited

    $ make live

#### Dev cycle

One branch derived from latest master per new feature or bug fix.

When this branch is complete:
- Merge master back in it
        
        $ git merge master
        
- Make sure all tests pass, the code is clean and the doc compiles:

        $ make
        
- Bump the version appropriately (no tags):

        $ bumpversion (major|minor|patch) --commit --no-tag
        
- Rebase everything in order to make one commit (if more are needed, talk the the maintainer). To avoid catastrophic failure, create another branch that won't be rebased first. Keep bumpversion's commit message somewhere in the rebased commit message, but not always on the first line.

        $ git branch <my_feature>_no_rebase
        $ git rebase -i master
        
- Make a pull request, or, if you are the maintainer, switch to master

        $ git checkout master
        
- If you are the maintainer, merge the feature branch:
        
        $ git merge <my_feature>
        
- If you are the maintainer, make sure everything works as it should

- If you are the maintainer, close the relevent issues (by adding fix... in the commit message with --amend)

- If you are the maintainer, create the appropriate tag

        $ git tag <version>

- If you are the maintainer, push the code to any relevant remote

        $ git push
        
- If you are the maintainer, upload the code to PyPI

        $ python3 setup.py sdist
        $ twine upload dist/*
        
- If you are the maintainer, check that the docs are updated

- If you are the maintainer or the devops guy, deploy the new code to all relevant machines

