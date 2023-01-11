#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place api --exclude=__init__.py
isort api --profile black
black api
