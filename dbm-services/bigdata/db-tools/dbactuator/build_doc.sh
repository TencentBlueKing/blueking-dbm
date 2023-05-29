#!/bin/bash

# https://github.com/swaggo/swag
# --parseDependency to avoid: ParseComment ... cannot find type definition: json.RawMessage
swag init -g cmd/cmd.go  --o docs/ --ot json,yaml --parseDependency
if [ $? -gt 0 ];then
  echo "generate swagger api docs failed"
  exit 1
fi
tree docs/