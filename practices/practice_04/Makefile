.PHONY: test venv clean

PYTHON ?= python3
PYTEST ?= pytest
VENV_DIR ?= .venv
PIP := $(VENV_DIR)/bin/pip
PYTHON_VENV := $(VENV_DIR)/bin/python
PYTEST_VENV := $(VENV_DIR)/bin/pytest

$(VENV_DIR)/bin/activate: 
	$(PYTHON) -m venv $(VENV_DIR)
	$(PYTHON_VENV) -m pip install --upgrade pip setuptools wheel
	$(PIP) install pytest mcp
	touch $(VENV_DIR)/bin/activate

venv: $(VENV_DIR)/bin/activate

test: venv
	PYTHONPATH=$(CURDIR) $(PYTEST_VENV) -q

clean:
	rm -rf $(VENV_DIR)
