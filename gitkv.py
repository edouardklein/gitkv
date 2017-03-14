"""
with gitkv.open(repo, file, mode="ab") as v:
    # il faudrait que v aie au moins l'interface d'un stream, selon le mode que l'on donne à gitkv.open()
    v.write("toto".encode())
    # Il faudrait également que v aie quelques autres champs, selon le besoin:
    v.commit()  # Return the last commit that modified file in repo
# En sortant du with, le commit est fait, et si c'est un repo distant, il est pushé

# Autre interface:

repo = gitkv.Repo("git@gitlab.lan:TOTO/TITI.git")

with repo.open(file) as v:
    # Same.

Not work in windows OS
gitkv only work in branch master

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


def open(repo, filename, mode='r', quiet=False):
    return FileInRepo(filename, repo, mode, OpenOneFile=True, quiet=quiet)


class Repo:
    """
    repo = Repo() ---> un repo temporaire, ne rien saugarder après la close
    repo =Repo(URL) -> clone 1 repo depuis URL dans dossier temporaire, push apres la close
        On peut utiliser ce mode pour repo local
        exemple : repo = Repo(/home/nguyen/exmple)
        /home/nguyen/exmple est un repository qui existe dans disk local
        configure /home/nguyen/exmple avec la comment "git config receive.denyCurrentBranch ignore" avant de appel gitkv
        Apres que gitkv push sur /home/nguyen/exmple
        Aller dans /home/nguyen/exmple et taper "git checkout -f" pour recuperer les contenus

    repo = Repo(path, diskLocal = True, newDirectory = True/False) -> Travaller sur dossier dans la disk local, comme
    ook version de Jeff
    # Si diskLocal n'est pas precisé, des bug sera indeterminé selon le cas, mettre True si utilser 1 dossier local
    repo.open(file, mode) ouvrir 1 fichier dans le repo
    # Non pour cette version, mais on peut ameliorer pour performance
        repo = (path,url)
            try
                git pull if repo on "path" exist in local
                git clone if repo on "path" not exist in local
            :except
                an error URL or git is not exist on URL
    """

    def __enter__(self):
        logging.info('Open a repository temporary :')
        return self

    def __init__(self, url="", diskLocal=False, newDirectory=False, quiet=False):
        """
        Function prepare the repository git
        :param url: url of git repo source, URL FTP recommended
            exemple : git@gitlab.lan:hailuan/repotest.git
            if a repo in disk local : /home/nguyen/exp/repotest/
        :param diskLocal: True if  repository in disk local
        :param newDirectory: True if we want make a directory if it doesn't exist, work on disk local
        """
        # open a temporary directory
        self.quiet = quiet
        self.push_url = False
        if not url: # repo = Repo() -> url None
            diskLocal = False
            self.tempDir = tempfile.TemporaryDirectory()
            self.tempDir_path = self.tempDir.name
            # un directory temporaire creer par tempfile n'est pas compatible avec init_repository de pygit2
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
        """
        Call and open (with io module) a file in Repository
        :return: stream interface for write or read file
            return Exception ValueError if file does not exist
        """
        logging.info('Open file ' + filename)
        return FileInRepo(filename, self.tempDir_path, modeFIR, quiet=self.quiet)

    def determine_func(self, name_module):
        """
        Call class MR for determine a module or a function
        :param name_module:
        :return:
        """
        modulename = importlib.import_module(str(name_module))
        Wrapper = MR(name_module, modulename, [self.tempDir_path])
        return Wrapper

    def __getattr__(self, item):
        return self.determine_func(item)

    def close(self):
        self.__exit__()

    class PushConflict (Exception):
        pass

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """
        Try to push all commit when close this repo
        close this class, all object in this class will be closed
        Exit when use "with Repo(url) as ..." statement or repo.close()
        While closed, push all data in this repo on git URL
        If conflict, raise exception PushConflict
        :param exc_type: type
        :param exc_val: value
        :param exc_tb: trace back
        :return:
        """
        # push before close this repo
        if self.push_url:
            Quiet = subprocess.DEVNULL if self.quiet else None
            with subprocess.Popen(['git', 'push'], cwd=self.tempDir_path, stdout=Quiet) as sp_push:
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
    """
    Exception raised when gitkv can't push in remote repository because a conflict
    """
    def __init__(self, data):
        self.data = data
    def __str__(self):
        return ('Error when push because a conflict !')
    pass

class MR:
    """
    Research module and function with a string
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
        """
        call a function Module_Func in module with paramettre in list self.listdata
        :param Module_Func:
        :param args:
        :param kwargs:
        :return:
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
    """
    While we use method wb, if the content recent of file is same the new one, no commit will be added
    Manager a file in repo, for open :

    fileinrepo = gitkv.open(repo,filename,mode)
    or
    repo = Repo(url)
    fileinrepo = repo.open(filename, mode)

    """

    def __enter__(self):
        # print('enter')
        return self

    def __init__(self, filename, path_repo, modeFIR='rb', OpenOneFile=False, quiet=False):
        self.quiet = quiet
        self.commit_message = 'GitKV : ' + filename
        self.OpenOneFile = OpenOneFile
        if self.OpenOneFile:
            self.repo = Repo(path_repo)
            self.path_repo = self.repo.tempDir_path
            # print ('Creer repo pour 1 file : ', self.path_repo)
        else:
            self.path_repo = path_repo
        self.filename = filename
        self.modeFIR = modeFIR
        # print (modeFIR)
        self.FileStreamIO = io.open(self.path_repo + self.filename, mode=modeFIR)
        # print ('Open IO ', path_repo + self.filename, ' mode ', self.modeFIR )
        logging.info('Open git commit for file ' + self.filename)
        # self.__enter__()

    def __iter__(self):
        return self.FileStreamIO.__iter__()

    def entry_in_commit(self, tree):
        """
        return entry having name = filename
        :param tree: tree of a commit
        :return: entry
        """
        for entry in tree:
            if entry.name == self.filename:
                return entry

    def utc_to_timestamp(str_utc):
        """
        Convert date type UCT to timestamp UNIX
        :param str_utc: date UTC (i.e : "2015-12-10 10:00:00+0000")
        :return: int timestamp (i.e. : 1450349553)
        """
        return time.mktime(datetime.datetime.strptime(str_utc, '%Y-%m-%d %H:%M:%S%z').timetuple())

    def gitlog(self, timeStart=0, timeEnd=32472140400, file_name_in_message=False):
        """
        Show commits of this file in repo since timeStart to timeEnd
        :param timeStar: type timestamp UNIX
        :param timeEnd: type timestamp UNIX
        :param file_name_in_message: file name in the message of commit,
        if True, just commits who have filename in message
            will be returned
            for the performance, try to save the file name in the commit is recommended
        :return: list data
            listdata[i]['id']
            listdata[i]['name']
            listdata[i]['data']
            listdata[i]['time']
        """
        repository = pygit2.Repository(self.path_repo)
        last = repository[repository.head.target]
        listcommit = []
        if file_name_in_message:
            # comprehension list en python ---> FIXED

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
        """
        Extract information of the file's last version
        :param choice: 'id'    -> id of last version
                       'time'  -> time last change
                       'data'  -> content binary of file
        :return:
        """
        try:
            repository = pygit2.Repository(self.path_repo)
        except KeyError:
            pygit2.init_repository(self.path_repo)  # create a repo git (not bare)
            repo = pygit2.Repository(self.path_repo)
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
        """
        close this class, all object in this class will be closed
        :param exc_type: type
        :param exc_val: value
        :param exc_tb: trace back
        :return: action exit
        """
        # add commit in repo if the file is changed when we use "io.open.write" method
        # close for save file in directory after write
        self.FileStreamIO.close()
        self.commit(self.commit_message)

        if self.OpenOneFile:
            self.repo.close()
