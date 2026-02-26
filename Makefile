PYTHON ?= $(shell if [ -x .venv311/bin/python ]; then echo .venv311/bin/python; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: test audit

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

audit:
	bash scripts/check_repo_size.sh
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
