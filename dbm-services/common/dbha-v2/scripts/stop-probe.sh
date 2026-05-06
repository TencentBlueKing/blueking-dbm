#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

echo "Stopping dbha-probe..."
./bin/dbha-probe stop -c ./etc/probe.yaml
if [ $? -eq 0 ]; then
    echo "dbha-probe stopped successfully."
else
    echo "Failed to stop dbha-probe." >&2
fi
