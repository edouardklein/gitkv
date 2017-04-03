"""``gitkv`` lets you use a git repo as a key-value store.


>>> # ... test setup ...
>>> import tempfile
>>> import pygit2
>>> tmpdir = tempfile.TemporaryDirectory()
>>> repo_url = tmpdir.name  # Here it is a local path
>>> gitrepo = pygit2.init_repository(repo_url, True)
>>> # The repo url can be anything that git recognizes as a git repo
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


class open():
    """Open a file in a repository.

    :param url: git repository where you want to open a file.
        It can be anything that is accepted by git, such as a relative
        or absolute path, a http ou https url, or a 'user@host:repo'-type url,
        etc.
    :param filename: tge file you want to open
    :param args, kwars: all other arguments are passed as is to the
        'true' ``open`` function
    :return: a stream-like object

    This method clones the repo in a local temporary directory.

    When ``close()`` is called on the returned object (or when one exits from
    the with block), an automatic commit is added to our clone, and is then
    pushed to the repo at ``url``
    """

    def __enter__(self):
        logging.info('Open a repository temporary :')
        return self

    def __init__(self, url, filename, *args, branch='master', **kwargs):
        self.repo = Repo(url, branch)
        self.fir = self.repo.open(filename, *args, **kwargs)

    def __getattr__(self, item):
        return self.fir.__getattr__(item)

    def close(self):
        self.fir.close()
        self.repo.close()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # add commit in repo if the file is changed when we use "io.open.write" method
        # close for save file in directory after write
        self.close()


class Repo:
    """A git repository.

    gitkv send a command push to git remote repository when this class is closing.

    An exception PushConflict will be returned when gitkv can't push on the remote
    because a conflict.

    If URL is a directory in disk local :\n
    Please config your git repository with the command before call gitkv.Repo(URL)

    - git config receive.denyCurrentBranch ignore

    For receive the content of the git repositry after a push from gitkv:

    - git checkout -f

    Class Repo composed many module who manage a repository or dirctory.

    For exemple module os :

    >>> import gitkv
    >>> with gitkv.Repo() as repository:
    ...     # For create a new directory in repository of class Repo :
    ...     repository.os.makedirs('toto_dir')
    ...     # For check with os.path.exists('dirs')
    ...     repository.os.path.exists('toto_dir')
    ...
    True
    """

    def __enter__(self):
        logging.info('Open a repository temporary :')
        return self

    def __init__(self, url=None, branch='master', newBranch=False):
        """Prepare for open a git repository

        :param url: url of git repo source, URL FTP recommended if you have a key ssh\n
            exemple : git@gitlab.lan:hailuan/repotest.git

        """
        # open a temporary directory
        self.url = url
        self.branch = branch
        create_branch = '-b' if newBranch else None
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
        # Prepare a clone repository for gitkv work on it
        self.tempDir = tempfile.TemporaryDirectory()
        self.tempDir_path = self.tempDir.name

        # try to clone the repo from git's url
        try:
            git_clone = subprocess.check_output(
                ['git', 'clone', self.url, 'gitkv_dir'],
                cwd=self.tempDir_path)
            logging.info('git clone {}:\n {}'.format(self.url, git_clone))
            self.tempDir_path = self.tempDir_path.rstrip('/') + '/gitkv_dir/'
            self.git_repo_tempo = pygit2.Repository(self.tempDir_path)

            # If the repository initial is empty, create a commit 'GitKV: commit initial'
            if (self.git_repo_tempo.is_empty):
                with io.open(self.tempDir_path + '.gitignore', 'w') as f:
                    pass
                    # git add .
                    try:
                        gitadd = subprocess.check_output(
                            ['git', 'add', '.gitignore'],
                            cwd=self.tempDir_path)
                        logging.info(gitadd)
                    except subprocess.CalledProcessError as e:
                        logging.info(e.output)
                    # git commit
                    try:
                        gitcommit = subprocess.check_output(
                            ['git', 'commit', '-m', "'GitKV: commit initial'"],
                            cwd=self.tempDir_path)
                        logging.info(gitcommit)
                    except subprocess.CalledProcessError as e:
                        logging.info(e.output)

            # git checkout branch
            try:
                if newBranch:
                    gitcheckout = subprocess.check_output(
                        ['git', 'checkout', '-b', self.branch],
                        cwd=self.tempDir_path)
                else:
                    gitcheckout = subprocess.check_output(
                        ['git', 'checkout', self.branch],
                        cwd=self.tempDir_path)
                logging.info(gitcheckout)
            except subprocess.CalledProcessError as e2:
                logging.info('git checkout {}:\n{}'.format(self.branch, e2.output))
                if self.branch != 'master':
                    raise ValueError

        except subprocess.CalledProcessError as e:
            logging.error('git clone {}:\n {}'.format(self.url, e.output))
            raise ValueError

    def open(self, filename, *args, **kwargs):
        """Call and open (with io module) a file in Repository

        :param: filename : the file name you want to open.
        :param: mode, *args, **kwargs : same when you call a stream object with 'io.open' methode.
        :return: a stream object for write or read file.

        """
        logging.info('Open file ' + filename)
        return FileInRepo(filename, self.tempDir_path, *args, **kwargs)

    def determine_func(self, name_module):
        # Search and import the function of another module and set
        # automatically the argument from this class to that function
        modulename = importlib.import_module(str(name_module))
        Wrapper = MR(name_module, modulename, self.tempDir_path)
        return Wrapper

    def recent_commit(self):
        last = self.git_repo_tempo[self.git_repo_tempo.head.target]
        commits = self.git_repo_tempo.walk(last.id, pygit2.GIT_SORT_TIME)
        for commit in commits:
            return commit

    def listFile(self, idCommit=None):
        if idCommit:
            commit = self.git_repo_tempo.get(idCommit)
        else:
            commit = self.recent_commit()

        for entry in commit.tree:
            yield entry.name

    def __iter__(self):
        return self.listFile().__iter__()

    def __getattr__(self, item):
        return self.determine_func(item)

    def close(self):
        """Closure the clone repository, send a push to git remote repository"""
        self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # git push wen closing
        try:
            gitpush = subprocess.check_output(['git', 'push', 'origin', self.branch],
                                              cwd=self.tempDir_path)
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
                gitpull = subprocess.check_output(['git', 'pull', 'origin', self.branch],
                                                  cwd=self.tempDir_path)
                logging.info(gitpull)
            except subprocess.CalledProcessError as e2:
                logging.error("Can't pull from {}, message error:"
                              "\n{}".format(self.url, e2.output))
            # Then push again
            try:
                gitpush2 = subprocess.check_output(['git', 'push', 'origin', self.branch],
                                                   cwd=self.tempDir_path)
                logging.info(gitpush2)
            except subprocess.CalledProcessError as e3:
                logging.error(e3.output)
                raise PushConflict(self)

        logging.info('Repository temporary Closed')
        # clean the temporary directory
        # self.tempDir.close()


class PushConflict(Exception):
    """Exception

    Exception raised when gitkv can't push in remote repository because a conflict
    """

    def __init__(self, data):
        self.data = data

    def __str__(self):
        return ('Error when push because a conflict !')


class MR:
    """Research module and function with a string
    be used in def __getattr__ of class FIR and Repo
    """

    def __init__(self, strModule, Module, Data_to_set_in):
        self.Module = Module
        self.Data_to_set_in = Data_to_set_in
        self.strModule = strModule

    def clone_func(self, Module_Func, *args, **kwargs):
        """call a function Module_Func in module with paramettre in list self.listdata
        """

        def fonction(*args, f=Module_Func, Data=self.Data_to_set_in, **kwargs):
            if isinstance(Data, str):
                return f(args[0] + Data, *args[1:], **kwargs)
            else:
                l = list(args)
                l.append(Data)
                return f(*l, **kwargs)

        return fonction

    def __getattr__(self, item):
        item_in_module = self.Module.__getattribute__(item)
        if isinstance(item_in_module, types.FunctionType):
            return self.clone_func(item_in_module, self.Data_to_set_in)
        else:
            nameModuleFils = str(self.strModule) + '.' + str(item)
            ModuleFils = importlib.import_module(nameModuleFils)
            newMR = MR(nameModuleFils, ModuleFils, self.Data_to_set_in)
            return newMR


class FileInRepo:
    """Manager a file in the git repository.

    # FIXME: Quand on ferme le FileInRepo, on doit pas fermer le repo
    # Mais il faut virer le flag booléen

    Create a commit if this file is modified at closure of this class

    Same class Repo, this class can call a function of another module and set
    automatically the content of a file to that function.
    Exemple with json module:

    >>> import gitkv
    >>> import json

    For exemple, you have a content json as content_json

    >>> content_json = json.loads('{"success" : "ok"}')

    You can call functions of module json with methode :

    >>> with gitkv.Repo() as repository:
    ...     # call function dump of json
    ...     with repository.open('jsonfile', mode='w') as jsonfile:
    ...         jsonfile.json.dump(content_json)
    ...     # call function loads of json
    ...     with repository.open('jsonfile', mode='r') as jsonfile:
    ...         result_json_load = jsonfile.json.load()
    ...

    >>> result_json_load['success']
    'ok'

    Same for module csv
    """

    def __enter__(self):
        return self

    def __init__(self, filename, path_repo, *args, **kwargs):
        """Prepare object, on gitkv, call this class from gitkv.open or Repo.open is recommanded

        """
        self.commit_message = 'GitKV: ' + filename
        self.path_repo = path_repo
        self.filename = filename
        self.FileStreamIO = io.open(self.path_repo + self.filename, *args, **kwargs)
        logging.info('Open git commit for file ' + self.filename)

    def __iter__(self):
        return self.FileStreamIO.__iter__()

    def entry_in_commit(self, tree):
        """return entry having the recent file

        :param tree: tree of a commit
        :return: a git's entry
        """
        for entry in tree:
            if entry.name == self.filename:
                return entry

    def utc_to_timestamp(str_utc):
        """Convert date type UCT to timestamp UNIX

        :param str_utc: date UTC (i.e : "2015-12-10 10:00:00+0000")
        :return: int timestamp (i.e. : 1450349553)
        """
        return time.mktime(datetime.datetime.strptime(str_utc, '%Y-%m-%d %H:%M:%S%z').timetuple())

    def gitlog(self, timeStart=0, timeEnd=float('inf'), file_name_in_message=False):
        """Show commits of this file in repo since timeStart to timeEnd

        :param timeStar: type timestamp UNIX
        :param timeEnd: type timestamp UNIX
        :param file_name_in_message: just commit where file's name in the message of commit
        :return: list of all versions of the file in all commit, type of element is dictionaire

        An exemple of usage : \n
        file = repository.open('file') \n
        version in file.gitlog() \n
        version[key]
        Key of data in objet json returned : \n
        'id' : id of last version. \n
        'time' : time last change. \n
        'data' : content binary of file. \n
        'idcommit' : the commit's id. \n
        'commit' : the commit's message. \n
        'name' : the entry's name. \n
        """
        repository = pygit2.Repository(self.path_repo)
        last = repository[repository.head.target]
        listcommit = []
        if file_name_in_message:
            for commit in [c for c in repository.walk(last.id, pygit2.GIT_SORT_TIME)
                           if self.filename in c.message and timeStart <= c.commit_time <= timeEnd]:
                # for commit in repository.walk(last.id, pygit2.GIT_SORT_TIME):
                # if self.filename in commit.message and timeStart <= commit.commit_time <= timeEnd:
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
                       if timeStart <= c.commit_time <= timeEnd]:
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

        version_recent()[choice]

        Argument choice: \n
        'id'      -> id of last version\n
        'time'    -> time last change \n
        'data'    -> content binary of file\n
        'idcommit'-> the commit's id \n
        'commit'  -> the commit's message \n
        'name'    -> the entry's name \n
        """
        try:
            repository = pygit2.Repository(self.path_repo)
        except KeyError:
            pygit2.init_repository(self.path_repo)  # create a repo git (not bare)
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
        # Search and import the function of another module and set
        # automatically the argument from this class to that function
        Module = importlib.import_module(str(name_module))
        Wrapper = MR(name_module, Module, self.FileStreamIO)
        return Wrapper

    def commit(self, message):
        """A commit will be added when this file in repository modified
        call this function if you want a another commit before the commit automatic.
        """
        # commentaire = '"' + message + '"'
        logging.info('From gitkv : Commit file ' + self.filename)
        # git add .
        try:
            message_output = subprocess.check_output(['git', 'add', '.'], cwd=self.path_repo)
            logging.info(message_output)
        except subprocess.CalledProcessError as e:
            logging.info(e.output)
        # logging.info('Commit : Add file change, succes = ' + str(sp_add.returncode))
        # git commit
        try:
            message_output = subprocess.check_output(['git', 'commit', '-m', message], cwd=self.path_repo)
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
        try:
            return self.__getattribute__(func)
        except AttributeError:
            try:
                return self.FileStreamIO.__getattribute__(func)
            except AttributeError:
                return self.determine_func(func)

    def close(self):
        """Close the stream object, a commit automatic will execute when the
        file is changed"""
        self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # add commit in repo if the file is changed when we use "io.open.write" method
        # close for save file in directory after write
        self.FileStreamIO.close()
        self.commit(self.commit_message)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
