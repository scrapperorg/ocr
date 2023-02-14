#!/bin/bash

set -e

echo "Running flake8"
flake8 .

echo "Running pytest..."
pytest --cov-branch --cov-report term --cov-report html:coverage -rfExX --color=yes .
