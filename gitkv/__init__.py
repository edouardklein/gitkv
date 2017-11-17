r"""``gitkv`` lets you use a git repo as a key-value store using
``open``-like semantics.


>>> import gitkv
>>> # ... test setup ...
>>> import tempfile
>>> tmpdir = tempfile.TemporaryDirectory()
>>> # The repo url can be anything that git recognizes
>>> # as a git repo
>>> repo_url = tmpdir.name  # Here it is a local path
>>> gitkv.Repo.git_init(repo_url, bare=True)
>>> # ... /test isetup ...
>>> with gitkv.open(repo_url, 'yourfile', 'w') as f:
...     f.write('Your content.')
13
>>> # When exiting the with block, a commit is created.
>>> # Later...
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     f.read()
'Your content.'
>>> # Multiple reads and writes can happen within one with block,
>>> # to avoid creating multiple commits,
>>> # by using the Repo class
>>> with gitkv.Repo(repo_url) as repo:
...     with repo.open('yourfile', 'a') as f:
...         f.write('\nAdditional content.')
...     data = repo.open('yourfile').read()
...     data = data.replace('Your', 'My')
...     with repo.open('yourfile', 'w') as f:
...         f.write(data)
...     with repo.open('anotherfile', 'w') as f:
...         f.write('something')
...     # The commit message may be specified before the block closes
...     repo.commit_message = 'Multiple edits'
20
31
9
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     [l.strip() for l in f]  # Files are iterable over their lines
['My content.', 'Additional content.']
>>> # A repo's history is accessible with the git_log() function
>>> repo = gitkv.Repo(repo_url)
>>> [repo.message(c).strip() for c in repo.git_log()]
['Multiple edits', 'GitKV: yourfile', 'GitKV: initial commit']
>>> # Which can be called on a file to get its specific history
>>> with gitkv.open(repo_url, 'anotherfile') as f:
...     [f.repo.message(c).strip() for c in f.git_log()]
['Multiple edits']
>>> # show the plain content of a file in a commit
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     commit = [c for c in f.git_log()
...                     if f.repo.message(c).strip() == 'GitKV: yourfile'][0]
...     f.show_blob(commit)
'Your content.'
"""

import io
import logging
import subprocess
import tempfile
import importlib
import os
import re

logger = logging.getLogger('gitkv')
logger.setLevel(level=logging.INFO)
__version__ = '1.1.1'


def run_cmd(cmd, **kwargs):
    '''Run a command, log it, raise on error, return the output.'''
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         **kwargs).decode('utf-8')
        logger.debug('{}\n\t{}'.format(' '.join(cmd),
                                       '\n\t'.join(output.split('\n'))))
        return output
    except subprocess.CalledProcessError as e:
        raise RuntimeError('{}\n{}'.format(' '.join(cmd), e.output))


class open:
    """Open a file in a repository.

    It is usually instanciated as a context manager.

    This method clones the repo in a local temporary directory.

    When ``close()`` is called on the returned object (e.g. when one exits from
    the with block), an automatic commit is added to our clone, and is then
    pushed to the repo at ``url``.
    """

    def __enter__(self):
        """Enter a ``with`` block"""
        return self

    def __init__(self, url, filename, *args, **kwargs):
        """Return the file-like object

            :param url: git repository where you want to open a file.
                It can be anything that is accepted by git, such as a relative
                or absolute path, a http or https url, or a ``user@host:repo``
                type url, etc. See :py:func:`Repo.__init__`
            :param filename: the file you want to open
            :param args kwargs: all other arguments are passed as is to the
                'true' ``open`` function
            :return: a stream-like object"""
        self.filename = filename
        self.repo = Repo(url)
        self.repo.commit_message = "GitKV: " + self.filename
        self.fir = self.repo.open(filename, *args, **kwargs)

    def __iter__(self):
        """Explicitely delegate __iter__ to our fir.

        Our __getattr__ trickery can not handle dunder methods, we need
        to explicietly pass the call.
        https://bugs.python.org/issue30352"""
        return self.fir.__iter__()

    def __getattr__(self, item):
        """Pass unknown attribute requests down to our FileInRepo instance"""
        return self.fir.__getattr__(item)

    def close(self):
        """Close our FileInRepo instance and our Repo instance.

        see :py:func:`Repo.close` and :py:func:`FileInRepo.close`"""
        self.fir.close()
        self.repo.remote_sync()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """"Exit a ``with`` block."""
        self.close()


class Repo:
    """A git repository.

    It is usually instanciated as a context manager.

    The provided repo is cloned. Upon the exiting the context, a commit is
    created and pushed to the original repo.

    An PushError exception will be raised when gitkv can't push on the
    remote because of a conflict.

    Some calls can be made within the context of the
    cloned repo, with automatic module importing:

    >>> import gitkv
    >>> with gitkv.Repo() as repo:
    ...     # Instead of
    ...     # import os
    ...     # os.makedirs(repo.path+'example/')
    ...     # one can write:
    ...     repo.os.makedirs('example/')
    ...     # it works as expected
    ...     import os
    ...     os.path.exists(repo.path+'example/')
    ...     # one could have written:
    ...     repo.os.path.exists('example/')
    ...
    True
    True

    The lookup is dynamic, any call that is not understood by ``Repo`` directly
    will lead to a call with the ``Repo``'s path attribute prepended to the
    first argument. Anything between the Repo and the function is interpreted
    as a module name.
    """

    def __enter__(self):
        """Start a ``with`` block."""
        return self

    def is_empty(self):
        '''Return True self is an empty repo'''
        try:
            run_cmd(['git', 'rev-list', 'HEAD'], cwd=self.path)
        except RuntimeError:  # Will fail if HEAD does not exist, i.e.
            return True  # if the repo is empty
        return False

    def initial_commit_if_empty(self):
        '''Commit an empty .gitignore file if the given repo is empty'''
        if not self.is_empty():
            return
        with self.open('.gitignore', 'w') as f:
            f.write('\n')
        self.git_commit("GitKV: initial commit")

    def __init__(self, url=None):
        """Return the context manager.

        :param url: git repository where you want to open a file.
            It can be anything that is accepted by git, such as a relative
            or absolute path, a http or https url, or a ``user@host:repo``
            type url, etc.

        If ``url`` is a directory with a non bare git repo in it, please
        configure your git repository beforehand:

        ``git config receive.denyCurrentBranch ignore``

        You will be able to checkout your changes with:

        ``git checkout -f``

        If ``url`` is None, an empty git repository is created in a
        temporary directory.
        """
        self.url = url
        if self.url is None:
            self.tmp_repo_dir = tempfile.TemporaryDirectory()
            self.url = self.tmp_repo_dir.name + '/'
            logger.info('Initialazing a temporary empty git repo: '
                        + self.url)
            self.git_init(self.url, bare=True)

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.path = self.tmp_dir.name + '/'
        self.branch = 'master'
        self.git_clone(self.url, self.path)
        self.initial_commit_if_empty()
        if url is None:
            self.git_push()
        self.commit_message = 'GitKV'

    def open(self, filename, *args, **kwargs):
        """Open a file in this Repo

        :param: filename: the file you want to open.
        :param: \*args, \*\*kwargs: all other arguments are passed as is
            to the 'true' ``open`` function.
        :return: a stream-like object
        """
        logger.debug('Opening file ' + filename)
        return FileInRepo(filename, self, *args, **kwargs)

    def __getattr__(self, item):
        """Call e.g. ``self.m.f(a, b, c)`` as ``self.m.f(self.path+a, b, c)``.

        Import all modules between self and f."""
        logger.debug("Repo getattr: " + item)

        def prepend_path_to_first_arg(*args):
            return [self.path + args[0]] + list(args[1:])

        return ModuleWrapper(item, prepend_path_to_first_arg)

    def list_files(self, id_commit='HEAD'):
        """List all files in repo in a commit."""
        return run_cmd(['git', 'ls-tree', '--name-only', id_commit],
                       cwd=self.path).split('\n')

    def __iter__(self):
        """Iterator over all the files in the last commit of the repo"""
        return self.list_files().__iter__()

    @staticmethod
    def git_clone(url, path):
        """Clone the remote repo at url in path."""
        run_cmd(['git', 'clone', url, path])

    def git_push(self):
        """Push to remote repository."""
        run_cmd(['git', 'push', 'origin', self.branch], cwd=self.path)

    def git_pull(self):
        """Pull from remote repository."""
        run_cmd(['git', 'pull', 'origin', self.branch], cwd=self.path)

    @staticmethod
    def git_init(path, bare=False):
        """"Initialize an empty repo at path."""
        run_cmd(['git', 'init'] + (['--bare'] if bare else []),
                cwd=path)

    def message(self, commit='HEAD'):
        """Return the commit message of the given commit."""
        return '\n'.join(run_cmd(['git', 'rev-list', '--format=%B',
                                  '--max-count=1',
                                  commit], cwd=self.path
                                 ).split('\n')[1:])

    def git_commit(self, message=None):
        """Create a commit."""
        if message is None:
            message = self.commit_message
        run_cmd(['git', 'add', '.'], cwd=self.path)
        try:
            run_cmd(['git', 'commit', '-m', message], cwd=self.path)
        except:
            pass

    def git_log(self, *options, custom_filter=lambda c: True):
        """Return the list of commits in reverse chronological order

        :param options: String array, will be passed as arguments to `git log`
        :param custom_filter: func, optional, filter commits according to an
             arbitrary criterion
        :return: list of commits,

        """
        command = ['git', 'log'] + list(options)
        gitlog_process_output = run_cmd(command, cwd=self.path)
        return [c for c in re.findall('(?<=commit )\w+',
                                      gitlog_process_output)
                if custom_filter(c)]

    def remote_sync(self):
        """Create a commit of our changes and push it to the remote repo."""
        # add a commit
        self.git_commit()
        # git push wen closing
        try:
            self.git_push()
        # if confict
        except RuntimeError:
            try:
                self.git_pull()
                self.git_push()
            except RuntimeError:
                raise PushError('Conflict when pushing')

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Exit a ``with`` block."""
        self.remote_sync()


class PushError(Exception):
    "Raised when gitkv can't push in a remote repository because a conflict."
    pass


class ModuleWrapper:
    """Dynamically import a module and change the arguments of a function."""
    module_name = None

    def __init__(self, item, arg_transform=lambda x: x):
        """Return the wrapper

        :param module:string the name of a module to
            import or of a function to call
        :param arg_transform:func *args are passed through
            this function before being given to item if item is callable
        """

        logger.debug("ModuleWrapper: " + item)
        self.module_name = item
        self.module = importlib.import_module(item)
        self.arg_transform = arg_transform

    def func_wrapper(self, func):
        """Return a wrapper over func that changes the arguments."""
        logger.debug("ModuleWrapper({}).{}".format(
            self.module_name,
            func))

        def wrapped_func(*args, f=func,
                         ft=self.arg_transform, **kwargs):
            """Actually call f with modified arguments"""
            logger.debug("ModuleWrapper({}).{}({})".format(
                self.module_name,
                func, *ft(*args)))
            return f(*ft(*args), **kwargs)

        return wrapped_func

    def __getattr__(self, attr):
        """Dynamically wrap a module or wrap a function"""
        logger.debug("ModuleWrapper({}).gettattr({})".format(self.module_name,
                                                             attr))
        item_in_module = self.module.__getattribute__(attr)
        logger.debug("ModuleWrapper: {}".format(item_in_module))
        if callable(item_in_module):
            return self.func_wrapper(item_in_module)
        else:
            next_attribute_name = str(self.module_name) + '.' + attr
            return ModuleWrapper(next_attribute_name, self.arg_transform)


class FileInRepo:
    """Manage a file in a git repository.

    Some calls can be made within the context of the
    FileInRepo object, with automatic module importing:\n
    For example with json module:

    >>> # ... test setup ...
    >>> # For exemple, a content type json as content_json
    >>> import json
    >>> content_json = json.loads('{"success" : "ok"}')
    >>> # ... /test setup ...
    >>>
    >>> # call functions of module json:
    >>> import gitkv
    >>> with gitkv.Repo() as repository:
    ...     # call function dump of json
    ...     with repository.open('jsonfile', mode='w') as jsonfile:
    ...         jsonfile.json.dump(content_json)
    ...     # call function loads of json
    ...     with repository.open('jsonfile', mode='r') as jsonfile:
    ...         result_json_load = jsonfile.json.load()
    >>> result_json_load['success']
    'ok'

    This mechanism works with any module, such as the csv module, for example.
    """

    def __enter__(self):
        """Start a ``with`` block."""
        return self

    def __init__(self, filename, repo, *args, **kwargs):
        """Return the context manager.

        This class should be instanciated with py:func:`gitkv.open` or
        py:func:`Repo.open`, and not directly.
        """
        self.commit_message = 'GitKV: ' + filename
        self.repo = repo  # gitkv object
        self.filename = filename
        self.fd = io.open(os.path.join(self.repo.path, self.filename),
                          *args, **kwargs)
        logger.debug('FileInRepo open ' + self.filename)

    def show_blob(self, commit='HEAD'):
        """Return the contents of self at a commit

        :param id_commit: type str, commit hex.
        :return: this file's data


        >>> import gitkv
        >>> repo = gitkv.Repo()
        >>> repo.os.makedirs('dossier')
        >>> with repo.open('dossier/afile', 'w') as f:
        ...     f.write('Initial')
        7
        >>> repo.remote_sync()
        >>> with repo.open('dossier/afile', 'w') as f:
        ...     f.write('Edit')
        4
        >>> repo.remote_sync()
        >>> with repo.open('dossier/afile') as f:
        ...     for cid in f.git_log():
        ...         print(f.show_blob(cid))
        Edit
        Initial

        """
        return run_cmd(['git', 'cat-file', 'blob',
                        '{}:{}'.format(commit, self.filename)],
                       cwd=self.repo.path)

    def git_log(self, *options):
        """Return a list of all commits that modified this instance's file,
        sorted from most recent to most ancient.

        :param options: String array, will be passed as arguments to `git log`

        :return: list of commits.

        >>> # ... test setup ...
        >>> import tempfile
        >>> import gitkv
        >>> import time
        >>> tmpdir = tempfile.TemporaryDirectory()
        >>> # The repo url can be anything that git recognizes
        >>> # as a git repo
        >>> repo_url = tmpdir.name  # Here it is a local path
        >>> gitkv.Repo.git_init(repo_url, bare=True)
        >>> # Simulate a conflict with 2 clones
        >>> repo_a = gitkv.Repo(repo_url)
        >>> with repo_a.open('myfile','w') as f:
        ...     f.write('Create myfile')
        13
        >>> repo_a.git_commit('Create myfile')
        >>> repo_a.remote_sync()
        >>> repo_b = gitkv.Repo(repo_url)
        >>> with repo_b.open('myfile','w') as f:
        ...     f.write('\\nB write')
        8
        >>> repo_b.git_commit('B write')
        >>> with repo_b.open('otherfile','w') as f:
        ...     f.write('Create otherfile')
        16
        >>> repo_b.git_commit('Create otherfile')
        >>> repo_b.remote_sync()
        >>> with repo_a.open('myfile','w') as f:
        ...     f.write('\\nA write')
        8
        >>> time.sleep(1)
        >>> repo_a.git_commit('A write')
        >>> # Error because a conflict
        >>> repo_a.remote_sync()
        Traceback (most recent call last):
        ...
        gitkv.PushError: Conflict when pushing
        >>> # Resolve this conflict
        >>> with repo_a.open('myfile','w') as f:
        ...     f.write('Create myfile\\nA write\\nB write')
        29
        >>> repo_a.git_commit('Merge')
        >>> repo_a.remote_sync()
        >>> # ... /test setup ...

        >>> # A commit history like this
        >>> # 0 <- Master   Merge
        >>> # |__
        >>> # 0  |          A write
        >>> # |  0          Create otherfile
        >>> # |  |
        >>> # |  0          B write
        >>> # |__|
        >>> #    0          Create myfile
        >>> #    |
        >>> #    0          GitKV: Initial commit

        >>> # Call git log of myfile
        >>> with gitkv.open(repo_url,'myfile') as f:
        ...     [f.repo.message(c).strip() for c in f.git_log('--date-order')]
        ['Merge', 'A write', 'B write', 'Create myfile']
        """
        return self.repo.git_log(*(list(options) + [self.filename]))

    def git_commit(self, message=None):
        """ Create a commit
        """
        # commentaire = '"' + message + '"'
        if message is None:
            message = self.commit_message
        logger.debug('From gitkv : Commit file ' + self.filename)
        # git add .
        run_cmd(['git', 'add', self.filename], cwd=self.repo.path)
        # git commit
        try:
            output = subprocess.check_output(
                ['git', 'commit', '-m', message],
                cwd=self.repo.path)
            logger.debug('{}\n\t{}'.format('git commit:\n\t',
                                           output))
        except subprocess.CalledProcessError as e:
            logger.debug(e.output)

    def __iter__(self):
        """Explicitely delegate __iter__ to our real file descriptor.

        Our __getattr__ trickery can not handle dunder methods, we need
        to explicietly pass the call.
        https://bugs.python.org/issue30352"""
        return self.fd.__iter__()

    def __getattr__(self, item):
        """Search attribute not defined in this class"""
        try:
            return self.__getattribute__(item)
        except AttributeError:
            try:
                return self.fd.__getattribute__(item)
            except AttributeError:

                def add_stream_as_last_arg(*args):
                    return list(args) + [self.fd]

                return ModuleWrapper(item, add_stream_as_last_arg)

    def close(self):
        """Close the stream object
        """
        self.fd.close()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Exit a ``with`` block."""
        # close stream object
        self.close()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
