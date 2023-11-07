SHELL := /bin/bash
BASE_DIR = $(shell pwd)
SRV_NAME=dbactuator_redis
VERSION = 0.0.1
GITHASH = ""

PACKAGE_PATH="dbm-services/redis/db-tools/dbactuator/cmd"

BUILD_FLAG = " -X ${PACKAGE_PATH}.version=${VERSION} -X ${PACKAGE_PATH}.buildstamp=`date -u '+%Y-%m-%d_%I:%M:%S%z'` -X ${PACKAGE_PATH}.githash=${GITHASH} "

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"   -ldflags ${BUILD_FLAG}  -o ${BASE_DIR}/build/$(SRV_NAME) -v main.go

clean:
	-rm ./bin/${SRV_NAME}

.PHONY: init clean build all
