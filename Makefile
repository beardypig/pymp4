# vim:noexpandtab:sw=2 ts=2

.PHONY: env

all: test

env/bin/activate: 
	test -d env || python3 -m venv env
	. env/bin/activate; \
		pip3 install -r requirements.txt

env: env/bin/activate

test: env
	. env/bin/activate; \
	coverage3 run -m pytest -s -v

clean:
	rm -rf env
	find . -name "*pycache*" -exec rm -fr "{}" \;
