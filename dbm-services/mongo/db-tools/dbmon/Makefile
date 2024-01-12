SRV_NAME=bk-dbmon
SHELL := /bin/bash
VERSION = 0.0.1
GITHASH = ""
MODULE="dbm-services/redis/db-tools/dbmon/cmd"
BUILD_FLAG = " -X ${MODULE}.version=${VERSION} -X ${MODULE}.githash=${GITHASH} -X ${MODULE}.buildstamp=`date +%Y-%m-%d_%H:%M:%S`"

local:
	CGO_ENABLED=0 go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"   -ldflags ${BUILD_FLAG}  -o ./build/$(SRV_NAME) -v main.go

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"   -ldflags ${BUILD_FLAG}  -o ./build/$(SRV_NAME) -v main.go

clean:
	rm -rf ./build && go clean -cache


.PHONY: init clean build
