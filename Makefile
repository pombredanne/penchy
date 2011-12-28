.PHONY: tests help hooks

help:
	@echo "Please use \`make <target>'"

tests:
	unit2 discover -s penchy/tests

hooks:
	ln -s $(realpath hooks/pre-commit) .git/hooks/pre-commit
