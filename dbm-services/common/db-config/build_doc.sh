#!/bin/bash

swag init -g cmd/bkconfigsvr/main.go --parseDependency
if [ $? -gt 0 ];then
  echo "generate swagger api docs failed"
  exit 1
fi
tree docs/