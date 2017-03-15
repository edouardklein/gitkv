import gitkv
import logging
from time import sleep
# Test mode local : repo = Repo()
import io
import json
"""
print('Test mode local ---------------------------------------------------')

#with gitkv.Repo() as repo_test :
with gitkv.Repo('/home/nguyen/exp/testlocal') as repo_test :
    for i in range (5) :

        with repo_test.open('FileExemple', 'w') as fir:
            fir.filedesc.write('Line ajoute chaque commit.' + str(i+40))
        with repo_test.open('OtherFile', 'w') as fir:
            fir.write('Line ajoute chaque commit file other.' + str(40 + i))
        sleep(1)

    with repo_test.open('OtherFile') as fir :
        l = fir.gitlog()
        for elt in l :
            print(elt['time'],' ',elt['data'])
    with repo_test.open('FileExemple') as fir:
        print('test recent')
        print(fir.version_recent().decode('utf-8'))

    with repo_test.open('jsonfile') as fir :
        print('test recent JSON : ')
        print(fir.version_recent().decode('utf-8'))
"""
"""
# Test repo git URL
with gitkv.Repo('git@gitlab.lan:hailuan/repotest.git') as repo_test :
    with repo_test.open('test_gitkv_7') as fir:
        print(fir.read())
"""
"""
# test mode URL, donner url de repo comme git@gitlab.lan:hailuan/repotest.git
for i in range(4) :
    with gitkv.Repo('git@gitlab.lan:hailuan/repotest.git') as repo_test :
        with repo_test.open('test_gitkv_7', 'wb') as fir :
            c = 'Test commit fois : ' + str(i)
            c1 = c.encode()
            print(c1)
            fir.write(c1)
            print ('Test : ok exit io')

        with repo_test.open('test_gitkv_8', 'r') as fir:

            print(fir.read())
"""

# test Json.dump, Json.load

"""
s = '{"success" : "ok", "new" : "try time 1"}'
Jss = json.loads(s)

with gitkv.Repo('/home/nguyen/exp/testlocal') as repo_test :
    print('Test 1 -------------------------------------------------')
    with repo_test.open('jsonfile','r') as fir :
        J1 = fir.json.loads()
        print('data type json before dump : ',J1)
        print(J1['new'], J1['success'])
    print ('Test 2 -------------------------------------------------')
    with repo_test.open('jsonfile', 'w') as fir :
        fir.json.dump(Jss)


    print('Test 3 -------------------------------------------------')
    with repo_test.open('jsonfile','rb') as fir :
        J1 = fir.json.loads()
        print('data type json after dump : ',J1)
        print(J1['new'], J1['success'])

"""
"""
# Test open one file
with gitkv.open('/home/nguyen/exp/testlocal', 'jsonfile', 'r') as fir :
    J1 = fir.json.loads()
    print('data type json after dump : ', J1)
    print(J1['new'], J1['success'])
"""

# Test repo.os.makedirs
"""
with gitkv.Repo() as repo:
    print('os.makedirs toto/')
    repo.os.makedirs('toto')
    print('Il existe le dossier toto dans le dossier tempo : ', repo.os.path.exists('toto'))
"""
with gitkv.Repo('/home/nguyen/exp/testlocal', quiet=True) as repo_test :

    with repo_test.open('jsonfile') as fir :
        l = fir.gitlog()
        for elt in l :
            print('-> ',elt['time'],elt['idcommit'],' ',elt['data'])
    with repo_test.open('FileExemple') as fir:
        print('-> test recent')
        print('->',fir.version_recent().decode('utf-8'))

    with repo_test.open('jsonfile') as fir :
        J1 = fir.json.loads()
        print(J1['new'], J1['success'])
    try :
        with repo_test.open('kjhdsqlkjh', 'r') as fir :
            fir.read()
    except FileNotFoundError:
        print ('nothing')

with gitkv.Repo() as repo :
    repo.os.makedirs ('toto')
    print(repo.os.path.exists('toto'))

