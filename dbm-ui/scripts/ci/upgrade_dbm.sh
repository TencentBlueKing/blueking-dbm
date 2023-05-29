#!/bin/bash


POD_BK_DBM=$(kubectl get pods -l app.kubernetes.io/name=dbm -o jsonpath="{.items[0].metadata.name}")
CONTAINERS_BK_DBM=$(kubectl get pods $POD_BK_DBM -o jsonpath='{.spec.containers[*].name}')
IMAGE_VERSION="${{BK_CI_MAJOR_VERSION}}.${{BK_CI_MINOR_VERSION}}.${{BK_CI_FIX_VERSION}}-alpha.${{BuildNo}}"
# IMAGE_VERSION="0.0.1-alpha.221"

NEW_VERSION="hub.tencent.com/blueking/bk-dbm:$IMAGE_VERSION"
for container in $CONTAINERS_BK_DBM; do
    echo "update container '$container' : kubectl set image deployments/bk-dbm $container=$NEW_VERSION"
    kubectl set image deployments/bk-dbm $container=$NEW_VERSION
done


DBM_JOB=$(kubectl get jobs -l app.kubernetes.io/name=dbm -o jsonpath="{.items[0].metadata.name}")
OLD_VERSION=$(kubectl get job $DBM_JOB -o jsonpath='{.spec.template.spec.containers[0].image}')
kubectl get job $DBM_JOB -o json | jq -r '.metadata.annotations."kubectl.kubernetes.io/last-applied-configuration"' > dbm_job.json

echo "create migrate job: $NEW_VERSION"
sed -i "s#$OLD_VERSION#$NEW_VERSION#g" ./dbm_job.json
cat ./dbm_job.json | grep "image\:"

echo "kubectl delete job $DBM_JOB"
kubectl delete job $DBM_JOB

echo "kubectl apply -f ./dbm_job.json"
kubectl apply -f ./dbm_job.json
