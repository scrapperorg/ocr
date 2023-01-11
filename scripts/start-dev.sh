#!/usr/bin/env bash

set -e

DEFAULT_MODULE_NAME=api.api

MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8080}
LOG_LEVEL=${LOG_LEVEL:-debug}
LOG_CONFIG=${LOG_CONFIG:-logging.ini}

COMMAND="uvicorn --host $HOST --port $PORT --log-level $LOG_LEVEL --log-config $LOG_CONFIG $APP_MODULE"

echo "Running '$COMMAND'"

# Start Uvicorn with live reload
exec $COMMAND