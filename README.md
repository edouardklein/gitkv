# Python Module Template FIXME(Change to your project's name)

## TODO FIXME(remove this section)

- Copy (do not clone, or you'll get all the template history) this repo somewhere
- Run

        $ make fixme

  to see all FIXMES than need to be fixed and fix them
  
- Run

        $ sphinx-quickstart
        
    And answer the questions so that :
    - the docs are in docs/
    - version and release both are 0.0.1
    - we use doctest and coverage.
- Init the git repo
        
        $ git init

- Set the intial version:
    
        $ bumpversion --new-version 0.0.1  # Par exemple
- Register your project on GitHub/GitLab:
    - Create the repo through the web interface
    
            $ git remote add origin <repo address>
            $ git add <relevant_files...>
            $ git push --set-upstream origin master
        
- Register your project on ReadTheDocs
- Register your project on PyPI

## Overview

FIXME(Project description)

## Installation

To install use pip:

    $ pip3 install FXIME(name)


Or clone the repo:

    $ git clone FIXME(repo url)
    $ python3 setup.py install
    
    

## Usage

### Documentation

Read the documentation FIXME(doc url) to understand how to use FIXME(name).

### In the cloned repo

#### Helper targets

To build the documentation, run:

    $ make doc
    
To run the test, run:

    $ make test

To check the code's superficial cleanliness run:

    $ make lint
    
To run tests each time a Python file is edited

    $ make live

#### Dev cycle

One branch derived from latest master per new feature or bug fix.

When this branch is complete:
- Merge master back in it
        
        $ git merge master
        
- Make sure all tests pass, the code is clean and the doc compiles:

        $ make
        
- Bump the version appropriately (no tags):

        $ bumpversion (major|minor|patch) --commit --no-tag
        
- Rebase everything in order to make one commit (if more are needed, talk the the maintainer). To avoid catastrophic failure, create another branch that won't be rebased first. Keep bumpversion's commit message somewhere in the rebased commit message, but not always on the first line.

        $ git branch <my_feature>_no_rebase
        $ git rebase -i master
        
- Make a pull request, or, if you are the maintainer, switch to master

        $ git checkout master
        
- If you are the maintainer, merge the feature branch:
        
        $ git merge <my_feature>
        
- If you are the maintainer, make sure everything works as it should

- If you are the maintainer, close the relevent issues (by adding fix... in the commit message with --amend)

- If you are the maintainer, create the appropriate tag

        $ git tag <version>

- If you are the maintainer, push the code to any relevant remote

        $ git push
        
- If you are the maintainer, upload the code to PyPI

        $ python3 setup.py sdist
        $ twine upload dist/*
        
- If you are the maintainer, check that the docs are updated

- If you are the maintainer or the devops guy, deploy the new code to all relevant machines

