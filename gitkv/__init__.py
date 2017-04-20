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
...     # commit automatic "GitKv"
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
...     # The commit may can be specified before the block closes
...     repo.set_commit_message('Multiple edits')
19
30
9
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     f.read()
'My content.Additional content.'
>>> # A repo's history is accessible with the git_log() function
>>> [l['commit'] for l in gitkv.Repo(repo_url).git_log()]
['Multiple edits', 'GitKV: yourfile', 'GitKV: initial commit']
>>> # Which can be called on a file to get its specific history
>>> with gitkv.open(repo_url, 'anotherfile') as f:
...     [l['commit'] for l in f.git_log()]
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

logging.basicConfig(level=logging.DEBUG)

__version__ = '0.0.1'


def run_cmd(cmd, **kwargs):  # FIXED function
    '''Run a command, log it, raise on error.'''
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                         **kwargs).decode('utf-8')
        logging.debug('{}\n\t{}'.format(' '.join(cmd),
                                        '\n\t'.join(output.split('\n'))))
    except subprocess.CalledProcessError as e:
        logging.error('{}\n{}'.format(' '.join(cmd), e.output))
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
        self.fir = self.repo.open(filename, *args, **kwargs)

    def __getattr__(self, item):
        """Pass unknown attribute requests down to our FileInRepo instance"""
        return self.fir.__getattr__(item)

    def close(self):
        """Close our FileInRepo instance and our Repo instance.

        see :py:func:`Repo.close` and :py:func:`FileInRepo.close`"""
        self.fir.close()
        self.repo.set_commit_message("GitKV: " + self.filename)
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

    def initial_commit_if_empty(self):  # FIXED: function
        '''Commit an empty .gitignore file if the given repo is empty'''

        if not self.repo.is_empty:
            return
        with self.open('.gitignore', 'w') as f:
            f.git_commit("GitKV: initial commit")

    def __init__(self, url=None):
        """Return the contect manager.

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
            logging.info('Initialazing a temporary empty git repo: '
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
        logging.debug('Opening file ' + filename)
        return FileInRepo(filename, self.path, *args, **kwargs)

    def __getattr__(self, item):
        """Call e.g. ``self.m.f(a, b, c)`` as ``self.m.f(self.path+a, b, c)``.

        Import all modules between self and f."""
        logging.debug("Repo getattr: " + item)

        def prepend_path_to_first_arg(*args):
            return [self.path + args[0]] + list(args[1:])

        return ModuleWrapper(item, prepend_path_to_first_arg)

    def last_commit(self):
        """Return the last commit"""
        return self.repo.head.get_object()  # Assume HEAD always point to the
        # last commit, as it should because we are the owner of our local repo

    def list_files(self, id_commit=None):
        """List all files in repo in a commit."""
        for entry in (self.repo.get(id_commit) if id_commit is not None
                      else self.last_commit()).tree:
            yield entry.name

    def __iter__(self):
        """Iterator over all the files in the last commit of the repo"""
        return self.list_files().__iter__()

    def set_commit_message(self, message):
        """ Change the message default of the commit automatic
        (commit when closing this class).

        A commit will be added when this file in repository modified
        Call this function if you want change the commit's message default.

        :param message: string, message commit
        """
        self.commit_message = message

    def git_clone(self, url, path):
        """Clone the remote repo at url in path."""
        run_cmd(['git', 'clone', url, path])

    def git_push(self):
        """Push to remote repository."""
        run_cmd(['git', 'push', 'origin', self.branch], cwd=self.path)

    def git_pull(self):
        """Pull from remote repository."""
        run_cmd(['git', 'pull', 'origin', self.branch], cwd=self.path)

    def git_commit(self, message=''):
        """Create a commit."""
        if message == '':
            message = self.commit_message
        run_cmd(['git', 'add', '.'], cwd=self.path)
        try:
            run_cmd(['git', 'commit', '-m', message], cwd=self.path)
        except:
            pass

    def git_log(self, timestart=0, timeend=float('inf')):
        """Show commits of this Repo since timestart to timeend

               :param timestart: type timestamp UNIX
               :param timeend: type timestamp UNIX
               :return: list of commits, type of element is dictionaire

               An exemple of usage : \n
               ``commits = repo.git_log()`` \n
               ``commit in commits`` \n
               ``commit[key]``\n

               All values of ``key``: \n
               ========== ================================
                  KEY              Description
               ========== ================================
               'time'      time of commit
               'idcommit'  the commit's id
               'commit'    the commit's message
               ========== ================================
        """

        listcommit = []
        repo = pygit2.Repository(self.path)
        last = repo[repo.head.target]
        for commit in [c for c in repo.walk(last.id)
                       if timestart <= c.commit_time <= timeend]:
            listcommit.append({
                'idcommit': commit.id,
                'commit': commit.message.rstrip('\n'),
                'time': commit.commit_time
            })
        return listcommit

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
    """Raised when gitkv can't push in a remote repository because a conflict"""
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

        logging.debug("ModuleWrapper: " + item)
        self.module_name = item
        self.module = importlib.import_module(item)
        self.arg_transform = arg_transform

    def func_wrapper(self, func):
        """Return a wrapper over func that changes the arguments."""
        logging.debug("ModuleWrapper({}).{}".format(
            self.module_name,
            func))

        def wrapped_func(*args, f=func,
                         ft=self.arg_transform, **kwargs):
            """Actually call f with modified arguments"""
            logging.debug("ModuleWrapper({}).{}({})".format(
                self.module_name,
                func, *ft(*args)))
            return f(*ft(*args), **kwargs)

        return wrapped_func

    def __getattr__(self, attr):
        """Dynamically wrap a module or wrap a function"""
        logging.debug("ModuleWrapper({}).gettattr({})".format(self.module_name, attr))
        item_in_module = self.module.__getattribute__(attr)
        logging.debug("ModuleWrapper: {}".format(item_in_module))
        if callable(item_in_module):  # FIXED: callable
            return self.func_wrapper(item_in_module)
        else:
            next_attribute_name = str(self.module_name) + '.' + attr
            return ModuleWrapper(next_attribute_name, self.arg_transform)


class FileInRepo:
    """Manager a file in the git repository.

    Some calls can be made within the context of the
    object FileInRepo, with automatic module importing:\n
    Exemple with json module:

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

    Same for module csv.
    """

    def __enter__(self):
        """enter bloc with"""
        return self

    def __init__(self, filename, path_repo, *args, **kwargs):
        """Prepare object, on gitkv,
        call this class from gitkv.open or Repo.open is recommanded
        """
        self.commit_message = 'GitKV: ' + filename
        self.path_repo = path_repo
        self.filename = filename
        self.object_io = io.open(self.path_repo + self.filename,
                                 *args, **kwargs)
        logging.info('Open git commit for file ' + self.filename)

    def __iter__(self):
        """Iterator for FileInRepo"""
        return self.object_io.__iter__()

    def entry_in_commit(self, tree):
        """return entry having the name of file

        :param tree: tree of a commit
        :return: a git's entry
        """
        for entry in tree:
            if entry.name == self.filename:
                return entry

    def utc_to_timestamp(self, str_utc):
        """Convert date type UCT to timestamp UNIX

        :param str_utc: date UTC (i.e : "2015-12-10 10:00:00+0000")
        :return: int timestamp (i.e. : 1450349553)
        """

        return time.mktime(
            datetime.datetime.strptime(
                str_utc,
                '%Y-%m-%d %H:%M:%S%z').timetuple()
        )

    def git_log(self, timestart=0, timeend=float('inf'),
                file_name_in_message=False):
        """Show commits of this file in repo since timestart to timeend

        :param timestart: type timestamp UNIX
        :param timeend: type timestamp UNIX
        :param file_name_in_message: just commit where file's name in the message of commit
        :return: list of all versions of the file in all commit, type of element is dictionaire

        An exemple of usage : \n
        ``f = repository.open('file')`` \n
        ``version in f.git_log()`` \n
        ``version[key]``\n
        All values of ``key``: \n
        ========== ================================
           KEY              Description
        ========== ================================
        'name'      the entry's name (file's name)
        'id'        entry' id
        'time'      time of commit
        'data'      content binary of file
        'idcommit'  the commit's id
        'commit'    the commit's message
        ========== ================================
        """
        repository = pygit2.Repository(self.path_repo)
        last = repository[repository.head.target]
        listcommit = []
        if file_name_in_message:
            for commit in [c for c in repository.walk(last.id, pygit2.GIT_SORT_TIME)
                           if self.filename in c.message
                           and timestart <= c.commit_time <= timeend]:
                tree = commit.tree
                entry = self.entry_in_commit(tree)
                if entry:
                    listcommit.append({
                        'idcommit': commit.id,
                        'commit': commit.message,
                        'id': entry.id,
                        'name': entry.name,
                        'data': repository[entry.id].data,
                        'time': commit.commit_time
                    })
            # print(listcommit.__len__())
            return listcommit
        # gitlog mode no file_name_in_message
        idtemp = None
        for commit in [c for c in repository.walk(last.id, pygit2.GIT_SORT_TIME)
                       if timestart <= c.commit_time <= timeend]:
            tree = commit.tree
            entry = self.entry_in_commit(tree)
            if entry and idtemp != entry.id:
                idtemp = entry.id
                listcommit.append({
                    'idcommit': commit.id,
                    'commit': commit.message.rstrip('\n'),
                    'id': entry.id,
                    'name': entry.name,
                    'data': repository[entry.id].data,
                    'time': commit.commit_time
                })
        # print (listcommit.__len__())
        return listcommit

    def version_recent(self):
        """Extract information of the recent version of file

        :return : object dictionnaire

        Exemple of usage:

        version_recent()[key]

        All value of key: \n
        ========== ================================
           KEY              Description
        ========== ================================
        'name'      the entry's name (file's name)
        'id'        entry' id
        'time'      time of commit
        'data'      content binary of file
        'idcommit'  the commit's id
        'commit'    the commit's message
        ========== ================================
        """
        repository = pygit2.Repository(self.path_repo)
        last = repository[repository.head.target]
        for commit in repository.walk(last.id):
            tree = commit.tree
            entry = self.entry_in_commit(tree)
            if entry:
                return {
                    'idcommit': commit.id,
                    'commit': commit.message.rstrip('\n'),
                    'id': entry.id,
                    'name': entry.name,
                    'data': repository[entry.id].data,
                    'time': commit.commit_time
                }

    def git_commit(self, message=''):
        """A commit will be added when this file in repository modified
        call this function if you want a another commit before the commit automatic.
        """
        # commentaire = '"' + message + '"'
        if message == '':
            message = self.commit_message
        logging.info('From gitkv : Commit file ' + self.filename)
        # git add .
        run_cmd(['git', 'add', '.'], cwd=self.path_repo)
        # git commit
        try:
            output = subprocess.check_output(
                ['git', 'commit', '-m', message],
                cwd=self.path_repo)
            logging.debug('{}\n\t{}'.format('git commit:\n\t',
                                            output))
        except subprocess.CalledProcessError as e:
            logging.debug(e.output)

    def set_commit_message(self, message):
        """ Change the message default of the commit automatic
        (commit when closing this class).

        A commit will be added when this file in repository modified
        Call this function if you want change the commit's message default.

        :param message: string, message commit
        """
        self.commit_message = message

    def __getattr__(self, item):
        """Search attribute not defined in this class"""
        try:
            return self.__getattribute__(item)
        except AttributeError:
            try:
                return self.object_io.__getattribute__(item)
            except AttributeError:

                def add_stream_as_last_arg(*args):
                    return list(args) + [self.object_io]

                return ModuleWrapper(item, add_stream_as_last_arg)

    def close(self):
        """Close the stream object, a commit automatic will execute when the
        file is changed.
        """
        self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Exit bloc with, call all function necessary for closure"""
        # add commit in repo if the file is changed
        # close for save file in directory after write
        self.object_io.close()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
