.PHONY: all checkdist clean cover lint sdist unit uploadtest upload

all: ;

checkdist: sdist
	twine check dist/*

clean:
	rm -fr ./build ./dist

cover:
	coverage run --source sshkernel --branch -m unittest discover tests/unit
	coverage report -m
	coverage html

lint:
	pylint sshkernel

sdist:
	python3 setup.py sdist bdist_wheel

unit:
	py.test sshkernel tests/unit --disable-pytest-warnings

uploadtest: sdist checkdist
	python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload: unit sdist checkdist
	python3 -m twine upload dist/*
