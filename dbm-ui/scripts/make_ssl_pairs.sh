#!/bin/bash

mkdir -p ./ssls && cd ./ssls

# create c/s ssl files
openssl genpkey -out server.key -algorithm RSA -pkeyopt rsa_keygen_bits:2048  > /dev/null 2>&1
openssl req -new -x509 -sha256 -days 36500 -key server.key -out server.crt -subj "/C=CN/O=BK/CN=DBM.SERVER"  > /dev/null 2>&1
openssl genpkey -out client.key -algorithm RSA -pkeyopt rsa_keygen_bits:2048  > /dev/null 2>&1
openssl req -new -subj "/C=CN/O=BK/CN=DBM.CLIENT" -key client.key -out client.csr  > /dev/null 2>&1
openssl x509 -req -sha256 -days 36500 -in client.csr -out client.crt -CA server.crt -CAkey server.key -set_serial 01  > /dev/null 2>&1

# clean tmp files
rm -rf client.csr
count=$(ls -l | grep "^-" | wc -l)
if [ "$count" -ne "4" ]; then
  echo "create c/s ssl files failed"
else
  echo "create c/s ssl files success"
fi
