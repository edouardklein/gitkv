"""``gitkv`` lets you use a git repo as a key-value store using
``open``-like sematics.


>>> # ... test setup ...
>>> import tempfile
>>> import pygit2
>>> tmpdir = tempfile.TemporaryDirectory()
>>> # The repo url can be anything that git recognizes
>>> # as a git repo
>>> repo_url = tmpdir.name  # Here it is a local path
>>> gitrepo = pygit2.init_repository(repo_url, True)
>>> # ... /test setup ...
>>> 
>>> import gitkv
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
...         f.write('Additional content.')
...     data = repo.open('yourfile').read()
...     data = data.replace('Your', 'My')
...     with repo.open('yourfile', 'w') as f:
...         f.write(data)
...     with repo.open('anotherfile', 'w') as f:
...         f.write('something')
...     # The commit message may be specified before the block closes
...     repo.commit_message = 'Multiple edits'
19
30
9
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     f.read()
'My content.Additional content.'
>>> # A repo's history is accessible with the git_log() function
>>> [c.message.strip() for c in gitkv.Repo(repo_url).git_log()]
['Multiple edits', 'GitKV: yourfile', 'GitKV: initial commit']
>>> # Which can be called on a file to get its specific history
>>> with gitkv.open(repo_url, 'anotherfile') as f:
...     [c.message.strip() for c in f.git_log()]
['Multiple edits']
"""
import io
import logging
import pygit2
import subprocess
import tempfile
import datetime
import time
import importlib
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('gitkv')
logger.setLevel(level=logging.DEBUG)

__version__ = '0.0.1'


def run_cmd(cmd, **kwargs):
    '''Run a command, log it, raise on error.'''
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         **kwargs).decode('utf-8')
        logger.debug('{}\n\t{}'.format(' '.join(cmd),
                                       '\n\t'.join(output.split('\n'))))
    except subprocess.CalledProcessError as e:
        logger.error('{}\n{}'.format(' '.join(cmd), e.output))
        raise RuntimeError


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

    def __getattr__(self, item):
        """Pass unknown attribute requests down to our FileInRepo instance"""
        return self.fir.__getattr__(item)

    def close(self):
        """Close our FileInRepo instance and our Repo instance.

        see :py:func:`Repo.close` and :py:func:`FileInRepo.close`"""
        self.fir.close()
        self.repo.close()

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

    def initial_commit_if_empty(self):
        '''Commit an empty .gitignore file if the given repo is empty'''

        if not self.repo.is_empty:
            return
        with self.open('.gitignore', 'w') as f:
            f.git_commit("GitKV: initial commit")

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
            pygit2.init_repository(self.url, True)

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.path = self.tmp_dir.name + '/'
        self.branch = 'master'
        self.git_clone(self.url, self.path)
        self.repo = pygit2.Repository(self.path)
        self.initial_commit_if_empty()
        if url is None:
            self.git_push()
        self.commit_message = 'GitKV'

    def open(self, filename, *args, **kwargs):
        """Open a file in this Repo

        :param: filename : the file you want to open.
        :param: *args, **kwargs : all other arguments are passed as is
            to the 'true' ``open`` function.
        :return: a stream-like object
        """
        logger.debug('Opening file ' + filename)
        return FileInRepo(filename, self.path, *args, **kwargs)

    def __getattr__(self, item):
        """Call e.g. ``self.m.f(a, b, c)`` as ``self.m.f(self.path+a, b, c)``.

        Import all modules between self and f."""
        logger.debug("Repo getattr: " + item)

        def prepend_path_to_first_arg(*args):
            return [self.path + args[0]] + list(args[1:])

        return ModuleWrapper(item, prepend_path_to_first_arg)

    def list_files(self, id_commit=None):
        """List all files in repo in a commit."""
        for entry in (self.repo.get(id_commit) if id_commit is not None
                      else self.git_log()[0]).tree:
            yield entry.name

    def __iter__(self):
        """Iterator over all the files in the last commit of the repo"""
        return self.list_files().__iter__()

    def git_clone(self, url, path):
        """Clone the remote repo at url in path."""
        run_cmd(['git', 'clone', url, path])

    def git_push(self):
        """Push to remote repository."""
        run_cmd(['git', 'push', 'origin', self.branch], cwd=self.path)

    def git_pull(self):
        """Pull from remote repository."""
        run_cmd(['git', 'pull', 'origin', self.branch], cwd=self.path)

    def git_commit(self, message=None):
        """Create a commit."""
        if message is None:
            message = self.commit_message
        run_cmd(['git', 'add', '.'], cwd=self.path)
        try:
            run_cmd(['git', 'commit', '-m', message], cwd=self.path)
        except:
            pass

    def git_log(self, timestart=0, timeend=float('inf')):
        """Return the list of commits from timestart to timeend,
        sorted ``from most recent to most ancient``.

               :param timestart, UNIX timestamp
               :param timeend, UNIX timestamp
               :return: list of commits,

        A commit is a
        `pygit2 Commit object <http://www.pygit2.org/objects.html#commits>`_.
        """
        repo = pygit2.Repository(self.path)
        flags = pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_TIME
        return [c for c in repo.walk(repo.head.target, flags)
                if timestart <= c.commit_time <= timeend]

    def close(self):
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
                raise PushError(self)

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Exit a ``with`` block."""
        self.close()


class PushError(Exception):
    """Raised when gitkv can't push in a remote repository because a conflict."""
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

    def __init__(self, filename, repo_path, *args, **kwargs):
        """Return the context manager.

        This class should be instanciated with py:func:`gitkv.open` or
        py:func:`Repo.open`, and not directly.
        """
        self.commit_message = 'GitKV: ' + filename
        self.repo_path = repo_path
        self.filename = filename
        self.fd = io.open(os.path.join(self.repo_path, self.filename),
                          *args, **kwargs)
        logger.debug('FileInRepo open ' + self.filename)

    def _entry_in_commit(self, tree):
        """Find the first entry in tree whose name is self.filename

        :param tree: tree of a commit
        :return: a git entry
        """
        for entry in tree:
            if entry.name == self.filename:
                return entry

    def utc_to_timestamp(self, str_utc):
        """Convert a date from UTC to UNIX timestamp

        :param str_utc: UTC date (i.e : "2015-12-10 10:00:00+0000")
        :return: int UNIX timestamp (i.e. : 1450349553)
        """

        return time.mktime(
            datetime.datetime.strptime(
                str_utc,
                '%Y-%m-%d %H:%M:%S%z').timetuple())

    def git_log(self, timestart=0, timeend=float('inf'),
                custom_filter=None):
        """Return a list of all commits that modified this instance's file,
        sorted from most recent to most ancient.

        :param timestart: UNIX timestamp, optional
        :param timeend: UNIX timestamp, optional
        :param custom_filter: func, optional, filter commits according to an
            arbitrary criterion
        :return: list of commits.

        A commit is a
        `pygit2 Commit object <http://www.pygit2.org/objects.html#commits>`_.

        """
        def safe_blame(repo, path, newest_commit):
            "Blame a commit for a file, return [] if it does not exist"
            try:
                return repo.blame(path, newest_commit=newest_commit)
            except KeyError:  # path did not exist in newest_commit
                return []

        repo = pygit2.Repository(self.repo_path)
        flags = pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_TIME
        sorted_commit_ids = [c.hex for c in repo.walk(repo.head.target, flags)
                             if timestart <= c.commit_time < timeend]
        if custom_filter is not None:
            blamed_ids = [c for c in sorted_commit_ids if
                          custom_filter(c)]
        else:
            blamed_ids = [i for c in sorted_commit_ids
                          for i in [h.final_commit_id
                                    for h in safe_blame(repo,
                                                        self.filename,
                                                        repo[c].id)]]
        return [repo[commit] for commit in sorted_commit_ids
                if commit in blamed_ids]

    def git_commit(self, message=None):
        """ Create a commit
        """
        # commentaire = '"' + message + '"'
        if message is None:
            message = self.commit_message
        logger.debug('From gitkv : Commit file ' + self.filename)
        # git add .
        run_cmd(['git', 'add', self.filename], cwd=self.repo_path)
        # git commit
        try:
            output = subprocess.check_output(
                ['git', 'commit', '-m', message],
                cwd=self.repo_path)
            logger.debug('{}\n\t{}'.format('git commit:\n\t',
                                           output))
        except subprocess.CalledProcessError as e:
            logger.debug(e.output)

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
