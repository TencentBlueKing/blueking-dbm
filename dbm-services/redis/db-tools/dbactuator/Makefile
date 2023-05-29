SHELL := /bin/bash
BASE_DIR = $(shell pwd)
SRV_NAME=dbactuator_redis
VERSION = 0.0.1
GITHASH = ""
MODULE="dbm-services/redis/db-tools/dbactuator/cmd"
BUILD_FLAG = " -X ${MODULE}.version=${VERSION} -X ${MODULE}.githash=${GITHASH} "

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${BUILD_FLAG}  -o ${BASE_DIR}/build/$(SRV_NAME) -v main.go

clean:
	rm -rf ./build/ && go clean -cache

.PHONY: init clean build all
