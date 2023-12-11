SHELL := /bin/bash
BASE_DIR = $(shell pwd)
VERSION = 0.0.1
GITHASH = ""
APPNAME = hadb-api
GOOS ?= linux
BUILD_FLAG = " -X main.version=${VERSION} -X main.githash=${GITHASH} "
BUILD_MINI_FLAG = " -s -w -X main.version=${VERSION} -X main.githash=${GITHASH} "

.PHONY: build mini clean gotool image

build:
	cd ${BASE_DIR} && CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build  -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"   -ldflags ${BUILD_FLAG}  -o $(BASE_DIR)/build/$(APPNAME) -v .

mini:
	cd ${BASE_DIR} && CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build  -gcflags=-trimpath=${PWD} -asmflags=-trimpath=${PWD}   -ldflags ${BUILD_MINI_FLAG}  -o $(BASE_DIR)/build/$(APPNAME) -v .
	upx $(BASE_DIR)/build/$(APPNAME)

clean:
	rm -rf ${BASE_DIR}/build && go clean -cache

gotool:
	-gofmt -w .
	-goimports -w . && find . -name go.mod -execdir go mod tidy \;

image: build
	docker build . -t mirrors.tencent.com/build/blueking/${APPNAME}:${VERSION}

help:
	echo "make - compile go source"
	echo "make gotool - run gofmt"
	echo "make image - compile and build image"
	echo "make clean - do some clean job"
