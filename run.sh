#!/bin/bash

ENV="test"

if [ "$1" == "prod" ]; then
    ENV="prod"
    echo "use prod config"
else
    echo "use test config"
fi

PROD=$([ "$ENV" == "prod" ] && echo "true" || echo "") uv run python main.py