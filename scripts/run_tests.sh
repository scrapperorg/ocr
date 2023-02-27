#!/bin/bash

set -e

echo "Running flake8"
flake8 ./app

echo "Running pytest..."
pytest -rfExX --color=yes .
#--cov-branch --cov-report term --cov-report html:coverage