SRV_NAME=bk-dbmon
SHELL := /bin/bash
VERSION = 0.0.1
GITHASH = `git rev-parse --short HEAD`
GOVERSION = $(shell go version)
MODULE="dbm-services/mongo/db-tools/dbmon/cmd"
BUILD_FLAG = -ldflags "-X '${MODULE}.version=${VERSION}' -X '${MODULE}.githash=${GITHASH}' -X '${MODULE}.buildstamp=`date +%FT%T%z`' -X '${MODULE}.goversion=${GOVERSION}' "
TRIMPATH = -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"
local:
	CGO_ENABLED=0 go build $(TRIMPATH)  -v $(BUILD_FLAG)   -o ./build/$(SRV_NAME) -v main.go

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  $(TRIMPATH) -v $(BUILD_FLAG)  -o ./build/$(SRV_NAME) -v main.go

clean:
	rm -rf ./build && go clean -cache


.PHONY: init clean build
