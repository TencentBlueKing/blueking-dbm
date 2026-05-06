#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

SERVICES="admin receiver analysis"

for svc in ${SERVICES}; do
    echo "Starting dbha-${svc}..."
    ./bin/dbha-${svc} daemon-start -c ./etc/${svc}.yaml
    if [ $? -eq 0 ]; then
        echo "dbha-${svc} started successfully."
    else
        echo "Failed to start dbha-${svc}." >&2
    fi
done
