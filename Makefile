.ONESHELL:
SHELL := /bin/bash

PROJECT := $(shell basename $(CURDIR))
PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_PYTHON_VERSION_SHORT := $(shell python -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')


install:
	@echo "This installer assumes you have pyenv installed and configured with python 3.9.7"
	# Check that current python version is 3.9.7
	@python --version | grep "Python 3.9.7" || (echo "Please install python 3.9.7 with pyenv" && exit 1)
	@poetry install
	@echo $(PROJECT_ROOT)/src > $(PROJECT_ROOT)/.venv/lib/python$(PROJECT_PYTHON_VERSION_SHORT)/site-packages/$(PROJECT).pth
	@echo $(PROJECT_ROOT)/src > $(PROJECT_ROOT)/.venv/lib64/python$(PROJECT_PYTHON_VERSION_SHORT)/site-packages/$(PROJECT).pth
	@echo "Project $(PROJECT) installed successfully"

doc: install
	@pdoc -o "./doc/" -f --http : src & xdg-open http://localhost:8080/src