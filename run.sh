#!/bin/bash

NAVI_PYTHON3="$(which python3.7)"

if [[ $NAVI_PYTHON3 == "" ]]; then
	NAVI_PYTHON3="$(which python3)"
fi

if [[ $NAVI_PYTHON3 == "" ]]; then
	NAVI_PYTHON3="$(which python)"
fi

if $NAVI_PYTHON3 --version | grep -o -E "^Python 3.7"; then
	$NAVI_PYTHON3 init.py
else
	echo "Python is not installed or version is not supported."
fi
