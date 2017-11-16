# Gitkv
## Overview

Use a git repo as a key-value store.

The key is the file name in the repo, and the value is the content of the file.

## Basic Usage

    import gitkv
    with gitkv.open(repo_url, fname) as f:
        data = f.read()
        f.write(do_womething_with(data))

## Rationale, pros and cons

The above example is reasonably ACID:

- This is **atomic**: if `do_something_with` fails, no data is pushed to the remote repo.
- **Consistency** can be checked with [git hooks](https://git-scm.com/book/gr/v2/Customizing-Git-Git-Hooks), most notably `pre-receive`.
- It is as **isolated** as the default conflict resolution of git can handle, which depending on your use case may not be enough. Also, in case of conflict, we only retry once. If you need rapid concurrent access, use a real database
- It is as **durable** as the filesystem you put your remote repo on is. Use hooks to ensure redundancy if needed.

GitKV is great if:
- You need to share a key value store across mutliple machines but don't want to manage a server
- You need to have a complete history of what happened or may need to retrieve past values
- You want to access your distributed key-value store with the `open`-like you're used with when dealing with files
- You want to easily inspect and modify the store 'by hand' (just ssh in and use your favorite text editor and git on the command line)
- You want stability and robustness

GitKV *really sucks* if:
- You need any performance at all (rapid fire access, huge values, reasonable access time, etc.)

## Advanced usage

See http://gitkv.readthedocs.io/

## Installation

    $ pip3 install gitkv


Or clone the repo:

    $ git clone https://github.com/edouardklein/gitkv.git
    $ python3 setup.py install

