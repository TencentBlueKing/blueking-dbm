#!/bin/bash

cd "$(dirname "$0")" || exit 1

echo "Starting dbha-probe..."
./bin/dbha-probe daemon-start -c ./etc/probe.yaml
if [ $? -eq 0 ]; then
    echo "dbha-probe started successfully."
else
    echo "Failed to start dbha-probe." >&2
fi
