"""``gitkv`` lets you use a git repo as a key-value store using
``open``-like sematics.


>>> # ... test setup ...
>>> import tempfile
>>> import pygit2
>>> tmpdir = tempfile.TemporaryDirectory()
>>> # The repo url can be anything that git recognizes as a git repo
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
19
30
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     f.read()
'My content.Additional content.'
>>> # One can get some info about a file's git history
>>> with gitkv.open(repo_url, 'yourfile') as f:
...     print(f.gitlog()[0]['commit'])
GitKV: yourfile
<BLANKLINE>

"""
import io
import logging
import pygit2
import subprocess
import tempfile
import datetime
import time
import importlib
import types

__version__ = '0.0.1'


class open:
    """Open a file in a repository.

    :param url: git repository where you want to open a file.
        It can be anything that is accepted by git, such as a relative
        or absolute path, a http or https url, or a ``user@host:repo`` type url,
        etc.
    :param filename: the file you want to open
    :param args kwargs: all other arguments are passed as is to the
        'true' ``open`` function
    :return: a stream-like object

    This method clones the repo in a local temporary directory.

    It is usually instanciated as a context manager.

    When ``close()`` is called on the returned object (e.g. when one exits from
    the with block), an automatic commit is added to our clone, and is then
    pushed to the repo at ``url``.
    """

    def __enter__(self):
        """Start bloc 'with'.
        """
        logging.info('Open a repository temporary :')
        return self

    def __init__(self, url, filename, *args, **kwargs):
        """Prepare object file in repo.
        """
        self.repo = Repo(url)
        self.fir = self.repo.open(filename, *args, **kwargs)

    def __getattr__(self, item):
        """Get attributes of class FileInRepo.

        :param item : name of a attribute
        """
        return self.fir.__getattr__(item)

    def close(self):
        """Close the stream object, a commit automatic will execute when the
        file is changed.
        """

        # add commit in repo if the file is changed
        self.fir.close()
        # then push on origin repository
        self.repo.close()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """exec function necessary before exit bloc 'with'."""

        # Close this class
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
    ...     # repo.os.path.exists('example/')
    ...
    True

    The lookup is dynamic, any call that is not understood by ``Repo`` directly
    will lead to a call with the ``Repo``'s path attribute prepended to the
    first argument. Anything between the Repo and the function is interpreted
    as a module name.
    """

    def __enter__(self):
        """Start bloc with"""
        logging.info('Open a repository temporary :')
        return self

    def __init__(self, url=None):
        """Prepare for open a git repository

        :param url: url of git repo source, URL FTP recommended if you have a key ssh\n
            exemple : git@gitlab.lan:hailuan/repotest.git

        If URL is a directory in disk local :\n
        Please config your git repository with the command before call gitkv.Repo(URL)

        - git config receive.denyCurrentBranch ignore

        For receive the content of the git repositry after a push from gitkv:

        - git checkout -f
        """

        # open a temporary directory
        if not url:  # repo = Repo() -> url None
            # Create a temporary git repository
            self.repo_tempo = tempfile.TemporaryDirectory()
            self.url = self.repo_tempo.name
            # un directory temporaire creer par tempfile n'est pas compatible
            #  avec init_repository de pygit2
            # solution : creer 1 dossier dans ce directory
            self.url = self.url.rstrip('/') + '/gitkv_url/'
            logging.warning('Repo temporaire ' + self.url)
            pygit2.init_repository(self.url, True)
        else:
            self.url = url

        # Prepare a clone repository
        self.tempDir = tempfile.TemporaryDirectory()
        self.path = self.tempDir.name
        self.branch = 'master'
        # try to clone the repository from git's url
        try:
            git_clone = subprocess.check_output(
                ['git', 'clone', self.url, 'gitkv_dir'],
                cwd=self.path)
            logging.info('git clone {}:\n {}'.format(self.url, git_clone))
        except subprocess.CalledProcessError as e:
            logging.error('git clone {}:\n {}'.format(self.url, e.output))
            raise ValueError
        self.path = self.path.rstrip('/') + '/gitkv_dir/'
        self.git_repo_tempo = pygit2.Repository(self.path)

        # If the repository initial is empty, create a commit 'GitKV: commit initial'
        # To limit somme bugs when the repository is empty.
        if self.git_repo_tempo.is_empty:
            with io.open(self.path + '.gitignore', 'w'):
                pass
                # git add .
            try:
                gitadd = subprocess.check_output(
                    ['git', 'add', '.gitignore'],
                    cwd=self.path)
                logging.info(gitadd)
            except subprocess.CalledProcessError as e:
                logging.info(e.output)
                # git commit
            try:
                gitcommit = subprocess.check_output(
                    ['git', 'commit', '-m', "'GitKV: commit initial'"],
                    cwd=self.path)
                logging.info(gitcommit)
            except subprocess.CalledProcessError as e:
                logging.info(e.output)

    def open(self, filename, *args, **kwargs):
        """Call and open (with io module) a file in Repository

        :param: filename : the file name you want to open.
        :param: mode, *args, **kwargs : all other arguments are passed as is
            to the 'true' ``open`` function.
        :return: a stream object for write or read file.

        """
        logging.info('Open file ' + filename)
        return FileInRepo(filename, self.path, *args, **kwargs)

    def determine_func(self, name_module):
        """ Search and import the function of another module and set
        automatically the argument from this class to that function
        """

        def transform_data(*args):
            l = list(args)
            l[0] = self.path + l[0]
            return l

        wrapper = MR(name_module, transform_data)
        return wrapper

    def recent_commit(self):
        last = self.git_repo_tempo[self.git_repo_tempo.head.target]
        commits = self.git_repo_tempo.walk(last.id, pygit2.GIT_SORT_TIME)
        for commit in commits:
            return commit

    def list_files(self, id_commit=None):
        if id_commit:
            commit = self.git_repo_tempo.get(id_commit)
        else:
            commit = self.recent_commit()

        for entry in commit.tree:
            yield entry.name

    def __iter__(self):
        """Iterator for Repo"""
        return self.list_files().__iter__()

    def __getattr__(self, item):
        """Search attribute not defined in this class"""
        return self.determine_func(item)

    def close(self):
        """Closure the clone repository, send a push to git remote repository"""
        self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Exit bloc with, call all function necessary for closure"""
        # git push wen closing
        try:
            gitpush = subprocess.check_output(
                ['git', 'push', 'origin', self.branch],
                cwd=self.path)
            logging.info(gitpush)
        except subprocess.CalledProcessError as e:
            logging.info(e.output)
            logging.warning("If git is a repo local,"
                            " try config your repo with this command before"
                            " execution of gitkv : \n "
                            "'git config receive.denyCurrentBranch ignore'")
            # if conflict
            # call a pull
            try:
                gitpull = subprocess.check_output(
                    ['git', 'pull', 'origin', self.branch],
                    cwd=self.path)
                logging.info(gitpull)
            except subprocess.CalledProcessError as e2:
                logging.error("Can't pull from {}, message error:"
                              "\n{}".format(self.url, e2.output))
            # Then push again
            try:
                gitpush2 = subprocess.check_output(
                    ['git', 'push', 'origin', self.branch],
                    cwd=self.path)
                logging.info(gitpush2)
            except subprocess.CalledProcessError as e3:
                logging.error(e3.output)
                raise PushError(self)

        logging.info('Repository temporary Closed')
        # clean the temporary directory
        # self.tempDir.close()


class PushError(Exception):
    """Exception

    Exception raised when gitkv can't push in remote repository because a conflict
    """

    def __str__(self):
        """Message of exception"""

        return "A conflict prevents the process push."

    def __init__(self, data):
        """Prepare exception.

        :param data: data saved for exception handling
        """
        self.data = data


class MR:
    """Research module and function with a string
    be used in def __getattr__ of class FIR and Repo
    """

    def __init__(self, namemodule, function_transform):
        """
        Prepare class MR.

        :param namemodule: type string
        :param function_transform:
        """

        self.namemodule = namemodule
        self.function_transform = function_transform

    def clone_func(self, function):
        """make an adapter function
        """

        function_transform = self.function_transform

        def fonction(*args, f=function,
                     ft=function_transform, **kwargs):
            """Edit arguments to fit with origin function
            and exec it"""
            return f(*ft(*args), **kwargs)

        return fonction

    def __getattr__(self, item):
        """Get attribute non definit in this class"""

        module = importlib.import_module(self.namemodule)
        item_in_module = module.__getattribute__(item)
        if isinstance(item_in_module, types.FunctionType):
            return self.clone_func(item_in_module)
        # when the attribute is not an attribute callable
        else:
            next_attribute_name = str(self.namemodule) + '.' + str(item)
            new_mr = MR(next_attribute_name, self.function_transform)
            return new_mr


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

    def gitlog(self, timestart=0, timeend=float('inf'),
               file_name_in_message=False):
        """Show commits of this file in repo since timestart to timeend

        :param timestart: type timestamp UNIX
        :param timeend: type timestamp UNIX
        :param file_name_in_message: just commit where file's name in the message of commit
        :return: list of all versions of the file in all commit, type of element is dictionaire

        An exemple of usage : \n
        file = repository.open('file') \n
        version in file.gitlog() \n
        version[key]\n
        All values of key: \n
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
                    'commit': commit.message,
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
        for commit in repository.walk(last.id, pygit2.GIT_SORT_TIME):
            tree = commit.tree
            entry = self.entry_in_commit(tree)
            if entry:
                return {
                    'idcommit': commit.id,
                    'commit': commit.message,
                    'id': entry.id,
                    'name': entry.name,
                    'data': repository[entry.id].data,
                    'time': commit.commit_time
                }

    def determine_func(self, name_module):
        """ Search and import the function of another module and set
        automatically the argument from this class to that function
        """
        oio = self.object_io

        def transform_data(*args):
            l = [oio]
            l = list(args) + l
            return l

        wrapper = MR(name_module, transform_data)
        return wrapper

    def commit(self, message):
        """A commit will be added when this file in repository modified
        call this function if you want a another commit before the commit automatic.
        """
        # commentaire = '"' + message + '"'
        logging.info('From gitkv : Commit file ' + self.filename)
        # git add .
        try:
            message_output = subprocess.check_output(['git', 'add', '.'],
                                                     cwd=self.path_repo)
            logging.info(message_output)
        except subprocess.CalledProcessError as e:
            logging.info(e.output)
        # logging.info('Commit : Add file change, succes = ' + str(sp_add.returncode))
        # git commit
        try:
            message_output = subprocess.check_output(
                ['git', 'commit', '-m', message],
                cwd=self.path_repo)
            logging.info(message_output)
        except subprocess.CalledProcessError as e:
            logging.info(e.output)

    def set_commit_message(self, message):
        """ Change the message default of the commit automatic
        (commit when closing this class).

        A commit will be added when this file in repository modified
        Call this function if you want change the commit's message default.

        :param message: string, message for commit
        """
        self.commit_message = message

    def __getattr__(self, func):
        """Search attribute not defined in this class"""
        try:
            return self.__getattribute__(func)
        except AttributeError:
            try:
                return self.object_io.__getattribute__(func)
            except AttributeError:
                return self.determine_func(func)

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
        self.commit(self.commit_message)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
