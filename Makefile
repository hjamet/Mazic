.ONESHELL:
SHELL := /bin/bash

PROJECT := $(shell basename $(CURDIR))
PROJECT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_PYTHON_VERSION_SHORT := $(shell python -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')

install:
	python -m venv .venv
	source .venv/bin/activate && pip install -r requirements.txt
	@echo $(PROJECT_ROOT)/src > $(PROJECT_ROOT)/.venv/lib/python$(PROJECT_PYTHON_VERSION_SHORT)/site-packages/$(PROJECT).pth
	@echo $(PROJECT_ROOT)/src > $(PROJECT_ROOT)/.venv/lib64/python$(PROJECT_PYTHON_VERSION_SHORT)/site-packages/$(PROJECT).pth