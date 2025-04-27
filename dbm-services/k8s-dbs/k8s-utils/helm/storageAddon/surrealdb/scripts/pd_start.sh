#!/bin/bash

# reference: tidb-operator's start script
# https://github.com/pingcap/tidb-operator/blob/master/pkg/manager/member/startscript/v2/pd_start_script.go

set -exo pipefail

SUBDOMAIN=${KB_CLUSTER_COMP_NAME}-headless
MY_PEER=$KB_POD_FQDN".cluster.local"

DATA_DIR="/var/lib/pd"
ARGS="--name=$HOSTNAME \
    --data-dir=$DATA_DIR \
    --peer-urls=http://0.0.0.0:2380 \
    --advertise-peer-urls=http://$MY_PEER:2380 \
    --client-urls=http://0.0.0.0:2379 \
    --advertise-client-urls=http://$MY_PEER:2379 \
    --config=/etc/pd/pd.toml"

# The /join detection is from tidb-operator's script.
# Normally when a pod restarts, pd reads cluster info from its persistent storage,
# and does not need --join args. So I suppose this is for the circumstance that
# a pod fails when during the cluster joining process.
if [[ -f $DATA_DIR/join ]]; then
    echo "restarted pod, join cluster"
    join=$(cat $DATA_DIR/join | tr "," "\n" | awk -F'=' '{print $2}' | tr "\n" ",")
    join=${join%,}
    ARGS="${ARGS} --join=${join}"
elif [[ ! -d $DATA_DIR/member/wal ]]; then
    echo "first started pod"
    replicas=$(echo "${KB_POD_LIST}" | tr ',' '\n')
    if [[ -n $KB_LEADER || -n $KB_FOLLOWERS ]]; then
        echo "joining an existing cluster"
        join=""

        for replica in $replicas; do
            host=${replica}.${SUBDOMAIN}.${DOMAIN}
            join="${join}http://$host:2380,"
        done

        join=${join%,}
        ARGS="${ARGS} --join=${join}"
    else
        echo "initializing a cluster"
        PEERS=""

        for replica in $replicas; do
            host=${replica}.${SUBDOMAIN}.${DOMAIN}
            PEERS="$PEERS$replica=http://$host:2380,"
        done

        PEERS=${PEERS%,}
        ARGS="${ARGS} --initial-cluster=${PEERS}"
    fi
fi
# restarted pod, initial cluster doesn't need --join or --initial-cluster args
exec /pd-server ${ARGS}
