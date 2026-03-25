#!/bin/bash

cd "$(dirname "$0")" || exit 1

SERVICES="admin receiver analysis"

for svc in ${SERVICES}; do
    echo "Stopping dbha-${svc}..."
    ./bin/dbha-${svc} stop -c ./etc/${svc}.yaml
    if [ $? -eq 0 ]; then
        echo "dbha-${svc} stopped successfully."
    else
        echo "Failed to stop dbha-${svc}." >&2
    fi
done
