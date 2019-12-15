#!/bin/bash

NAVI_PYTHON3="$(which python3.7)"

if [[ $NAVI_PYTHON3 == "" ]]; then
	NAVI_PYTHON3="$(which python3)"
fi

if [[ $NAVI_PYTHON3 == "" ]]; then
	NAVI_PYTHON3="$(which python)"
fi

$NAVI_PYTHON3 init.py
