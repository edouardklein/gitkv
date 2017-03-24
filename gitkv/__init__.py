"""gikv is a python's module use a git repo as a key-value store.

This module use git and python pygit2 so please check if they are properly installed
gitkv work on a temporary directory as a git repository cloned from a URL or a path local.

>>> import gitkv

For use gitkv, input a url of repository, if url = None, gitkv work on a new repository
and it will be remove after.

>>> URL = None

An exemple of usage :

>>> with gitkv.Repo(URL,quiet=True) as repository:
...     # open a file in the repository for write :
...     with repository.open('file', modeFIR='w') as file:  # FIXME: La syntaxe de repository.open doit être la même que celle de open
...                                                         # FIXME S'assurer que ça marche avec la syntaxe repository.open('file', mode='w')
...         file.write('write on your file')
...     # And read it :
...     with repository.open('file', modeFIR='r') as file:  # FIXME: S'assurer que ça marche avec la syntaxe repository.open('file', 'r')
...         print(file.read())
...
write on your file
18  # FIXME: Pas de 18
>>> content_read
'write on your file'

Remarque :
    Not work in windows OS. \n
    gitkv only work in branch master of the repository.
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

__author__ = 'Edouard Klein'
__email__ = 'edouardklein -at- gmail.com'
__version__ = '0.0.1'


def open(repo, filename, mode='r', quiet=False):
    # FIXME Ecrire une docstring et utiliser
    # with gitkv.open(repo, fname, 'w') as f:
    #     f.write(data)
    # comme exemple
    # Il faut aussi que cet exemple:
    # with gitkv.open(repo, fname) as f:
    #      data = f.json.load()
    # fonctionne.
    # Idem pour le dump:
    # http://gitlab.lan/hailuan/GitKv/issues/1
    return FileInRepo(filename, repo, mode, OpenOneFile=True, quiet=quiet)


class Repo:
    """Open a git repository from an URL.

    repo = Repo() ---> a temporary repository. \n
    repo = Repo(URL) -> clone a git repository from URL, push after the closure. \n
    Exemple for URL :\n
    URL = '/home/root/GitRepo' \n
    URL = 'https://github.com/edouardklein/gitkv.git'

    gitkv send a command push to git remote repository when this class is closing.
    + repo.close() \n
    + usage statement with \n
    An exception PushConflict will be returned when gitkv can't push on the remote
    because a conflict.

    If URL is a directory in disk local :\n
    Please config your git repository with the command before call gitkv.Repo(URL)

    > git config receive.denyCurrentBranch ignore

    For receive the content of the git repositry after a push from gitkv:

    > git checkout -f

    gitkv offers a way to work directly on your git repository local:

    repository = gitkv.Repo(URL, diskLocal = True, newDirectory = False)

    Set newDirectory = True if you want create a new git repository.
    This mode is not recommanded if you want work with multi-thread.

    Class Repo composed many module who manage a repository or dirctory.

    For exemple module os :

    >>> import gitkv
    >>> with gitkv.Repo(quiet=True) as repository:
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

    def __init__(self, url="", diskLocal=False, newDirectory=False, quiet=False):
        """Function prepare the repository git

        :param url: url of git repo source, URL FTP recommended if you have a key ssh
            exemple : git@gitlab.lan:hailuan/repotest.git
        :param diskLocal: True if work drectly on git repository in disk local
        :param newDirectory: True if you want make a directory if it doesn't
         exist, only work on disk local
        """
        # open a temporary directory
        self.quiet = quiet
        self.push_url = False
        if not url:  # repo = Repo() -> url None
            diskLocal = False
            self.tempDir = tempfile.TemporaryDirectory()
            self.tempDir_path = self.tempDir.name
            # un directory temporaire creer par tempfile n'est pas compatible
            #  avec init_repository de pygit2
            # solution : creer 1 dossier dans ce directory
            self.tempDir_path = self.tempDir_path.rstrip('/') + '/gitkv_dir/'
            logging.warning('Repo temporaire ' + self.tempDir_path)
            pygit2.init_repository(self.tempDir_path)
        elif diskLocal:
            self.tempDir_path = url.rstrip('/') + '/'
            if not newDirectory:
                pygit2.Repository(self.tempDir_path)
            else:  # Create a repository if path is not repository or not doesn't exist
                try:
                    pygit2.Repository(self.tempDir_path)
                except KeyError:
                    pygit2.init_repository(self.tempDir_path)
        else:
            self.tempDir = tempfile.TemporaryDirectory()
            self.tempDir_path = self.tempDir.name
            # try to clone the repo from git's url
            listProcess = ['git', 'clone', url, 'gitkv_dir']
            Quiet = subprocess.DEVNULL if self.quiet else None
            with subprocess.Popen(listProcess, cwd=self.tempDir_path,
                                  stdout=Quiet) as sp:
                sp.wait()
            # subprocess git clone finish
            if sp.returncode == 0:  # clone success
                logging.info('Clone from ' + url + ' success')
                self.tempDir_path = self.tempDir_path.rstrip('/') + '/gitkv_dir/'
                # faire 1 push avant de close
                self.push_url = True
            else:  # Error of URL of repo git
                raise ValueError

    def open(self, filename, modeFIR='rb'):
        """Call and open (with io module) a file in Repository

        :return: stream interface for write or read file
        """
        logging.info('Open file ' + filename)
        return FileInRepo(filename, self.tempDir_path, modeFIR, quiet=self.quiet)

    def determine_func(self, name_module):
        """Search and import the function of another module and set
        automatically the argument from this class to that function
        """
        modulename = importlib.import_module(str(name_module))
        Wrapper = MR(name_module, modulename, [self.tempDir_path])
        return Wrapper

    def __getattr__(self, item):
        return self.determine_func(item)

    def close(self):
        self.__exit__()

    class PushConflict(Exception):
        pass

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if self.push_url:
            Quiet = subprocess.DEVNULL if self.quiet else None
            with subprocess.Popen(['git', 'push'],
                                  cwd=self.tempDir_path,
                                  stdout=Quiet
                                  ) as sp_push:
                sp_push.wait()
            if sp_push.returncode == 1:
                logging.warning("If git is a repo local, try config your repo with : \n "
                                "'git config receive.denyCurrentBranch ignore'  before execution of gitkv\n"
                                "Then go to remote repository, type 'git checkout -f'")
                # if conflict
                # call a pull
                with subprocess.Popen(['git', 'pull', '--no-log'], cwd=self.tempDir_path) as sp_pull:
                    sp_pull.wait()
                # then push
                with subprocess.Popen(['git', 'push'], cwd=self.tempDir_path) as sp_push:
                    sp_push.wait()

                # FIX cas repo local
                if sp_push.returncode == 1:
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

    pass


class MR:
    """Research module and function with a string
    be used in def __getattr__ of class FIR and Repo
    """

    def __init__(self, strModule, Module, listData):
        self.Module = Module
        self.listData = listData
        self.strModule = strModule

    def TryAll(self, listTry, Func, *args1, **kwargs1):
        if not listTry:
            return Func(*args1, **kwargs1)
        try:
            try:
                a = listTry[0] + args1[0]
                return Func(a, **kwargs1)
            except:
                a = list(args1)
                a.append(listTry[0])
                # print(a)
                return Func(*a, **kwargs1)
        except:
            del listTry[0]
            return self.TryAll(listTry, Func, *args1, **kwargs1)

    def clone_func(self, Module_Func, *args, **kwargs):
        """call a function Module_Func in module with paramettre in list self.listdata
        """
        lD = self.listData

        def fonction(*args, f=Module_Func, listData=lD, **kwargs):
            return self.TryAll(listData, f, *args, **kwargs)

        return fonction

    def __getattr__(self, item):
        item_in_module = self.Module.__getattribute__(item)
        if isinstance(item_in_module, types.FunctionType):
            return self.clone_func(item_in_module, self.listData)
        else:
            nameModuleFils = str(self.strModule) + '.' + str(item)
            ModuleFils = importlib.import_module(nameModuleFils)
            newMR = MR(nameModuleFils, ModuleFils, self.listData[:])
            return newMR


class FileInRepo:
    """Manager a file in the git repository.

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
    ...     with repository.open('jsonfile', modeFIR='w') as jsonfile:
    ...         jsonfile.json.dump(content_json)
    ...     # call function loads of json
    ...     with repository.open('jsonfile', modeFIR='r') as jsonfile:
    ...         result_json_load = jsonfile.json.loads()
    ...

    >>> result_json_load['success']
    'ok'

    Same for module csv
    """

    def __enter__(self):
        return self

    def __init__(self, filename, path_repo, modeFIR='rb', OpenOneFile=False, quiet=False):
        self.quiet = quiet
        self.commit_message = 'GitKV : ' + filename
        self.OpenOneFile = OpenOneFile
        if self.OpenOneFile:
            self.repo = Repo(path_repo)
            self.path_repo = self.repo.tempDir_path
        else:
            self.path_repo = path_repo
        self.filename = filename
        self.modeFIR = modeFIR
        self.FileStreamIO = io.open(self.path_repo + self.filename, mode=modeFIR)
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

    def gitlog(self, timeStart=0, timeEnd=32472140400, file_name_in_message=False):
        """Show commits of this file in repo since timeStart to timeEnd

        :param timeStar: type timestamp UNIX
        :param timeEnd: type timestamp UNIX
        :param file_name_in_message: just commit where file's name in the message of commit
        :return: list of all versions of the file in all commit, type of element is json

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

    def version_recent(self, choice='data'):
        """Extract information of the file's last version

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
                if choice == 'data':
                    return repository[entry.id].data
                elif choice == 'id':
                    return entry.id
                elif choice == 'time':
                    return commit.commit_time

    def determine_func(self, name_module):
        Module = importlib.import_module(str(name_module))
        if (self.modeFIR == 'r' or self.modeFIR == 'rb'):
            textB = self.FileStreamIO.read()
            try:
                textB = textB.decode('utf-8')
            except:
                pass
            Wrapper = MR(name_module, Module, [self.FileStreamIO, textB])
        else:
            Wrapper = MR(name_module, Module, [self.FileStreamIO])
        return Wrapper

    def commit(self, message):
        """A commit will be added when this file in repository modified
        call this function if you want a another commit before the commit automatic.
        """
        commentaire = '"' + message + '"'
        logging.info('From gitkv : Commit file ' + self.filename)
        # git add .
        with subprocess.Popen(['git', 'add', '.'], cwd=self.path_repo) as sp_add:
            sp_add.wait()
        # logging.info('Commit : Add file change, succes = ' + str(sp_add.returncode))
        # git commit
        listProcess = ['git', 'commit', '-m', commentaire]
        Quiet = subprocess.DEVNULL if self.quiet else None
        with subprocess.Popen(listProcess, cwd=self.path_repo, stdout=Quiet) as sp_commit:
            sp_commit.wait()
            # logging.info('Commit : commit file, success = ' + str(sp_commit.returncode))

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
            if str(func) == 'filedesc':
                return self.FileStreamIO
            else:
                return self.FileStreamIO.__getattribute__(func)
        except:
            return self.determine_func(func)

    def close(self):
        self.__exit__()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # add commit in repo if the file is changed when we use "io.open.write" method
        # close for save file in directory after write
        self.FileStreamIO.close()
        self.commit(self.commit_message)

        if self.OpenOneFile:
            self.repo.close()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
