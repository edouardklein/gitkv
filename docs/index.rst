.. gitkv documentation master file, created by
   sphinx-quickstart on Thu Mar 23 12:49:22 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to gitkv's documentation!
=================================

.. automodule:: gitkv
    :members: open, Repo, FileInRepo, PushError
    :special-members: __init__


Installation
==================

:code:`gitkv` depends on :code:`libgit2`, which in turns depends on :code:`cffi`.
:code:`pip` can not,
unfortunately, install those dependencies. You should use your system's package
manager or install them from source. On a Debian host, one can run:

:code:`# apt-get install libcffi-dev libgit2-dev`

The :code:`pygit2` python package should then be installed in a version that
matches your system's
version of libgit2. You can know which version that is by running:

:code:`$ apt-cache show libgit2-dev`

You can then install the matching python package (in our case version 0.21):

:code:`# pip3 install pytgit2==0.21`

Now, installing `gitkv` should work via pip:

:code:`# pip3 install gitkv`
