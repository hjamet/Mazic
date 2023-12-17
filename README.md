[![libera manifesto](https://img.shields.io/badge/libera-manifesto-lightgrey.svg)](https://liberamanifesto.com)

# Mazic

## Description

Mazic is a cooperative game in which you take on the role of a group of mages who are foolish or foolhardy enough to travel to a magical labyrinth infested by the worst creatures of the shadows in order to recover artefacts that can multiply their power. Alas, a terrifying legend has it that the souls of the mages who failed in their quest are trapped in the labyrinth and haunt the place, ready to do anything to prevent newcomers from escaping.

## Installation 🐼

You can alternatively create a virtual environment, install the dependencies and run the src/main.py file from the root of the repository.
Or you can run the Makefile with the following command :

```
> make install
```

### You just want to play the Game...

Just go to the release tab and download last game version ! 💃

## Do you want to get your hands dirty?

> **We are assuming you have python 3.9.7 installed !**

```
> python -m venv env
> source env/bin/activate
> python -m pip install -r requirements.txt
> python src/main.py
```

## Repository Convention & Architecture 🦥

### Architecture 🦜

* The notebooks folder contains the notebooks that we will return with our results
* All algorithms performing complex or persistent operations must be implemented in the src folder, one file per feature. Give preference to object-oriented programming. These objects will then be called in the notebooks.
* We use Poetry for managing virtual environments & installing dependencies. See
    * https://python-poetry.org/
    * https://github.com/pyenv/pyenv

### Convention 🦦

* **[DOCSTRING]** : We use typed google docstrings for all functions and methods. See https://www.python.org/dev/peps/pep-0484/ and https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html . Docstring and notebooks should be written in English.
* **[TEST]** : All files in src should be summarily tested. Ideally, leave a simplistic example of use commented out at the bottom of each file to demonstrate its use. No need to use PyTest absolutely, we're not monsters either :D
* **[GIT]** : We use the the commit convention described here: https://www.conventionalcommits.org/en/v1.0.0/ . You should never work on master, but on a branch named after the feature you are working after opening an issue to let other members know what you are working on so that you can discuss it. When you are done, you can open a pull request to merge your branch into master. We will then review your code and merge it if everything is ok. Issues and pull requests can be written in French.

> Of course, anyone who doesn't follow these rules, arbitrarily written by a tyrannical mind, is subject to judgmental looks, cookie embargoes and denunciatory messages with angry animal emojis.
