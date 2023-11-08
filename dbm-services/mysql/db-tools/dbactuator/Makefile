SHELL := /bin/bash
BASE_DIR = $(shell pwd)
VERSION = 0.0.1
GITHASH = ""
APPNAME = dbactuator
GOOS ?= linux
BUILD_FLAG = " -X main.version=${VERSION} -X main.githash=${GITHASH} "
BUILD_EXTERNAL_FLAG = " -X main.external=ON -X main.version=${VERSION} -X main.githash=${GITHASH} "
BUILD_MINI_FLAG = " -s -w -X main.version=${VERSION} -X main.githash=${GITHASH} "

.PHONY: all build clean

build:
	cd ${BASE_DIR}/cmd && CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build  -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"   -ldflags ${BUILD_FLAG}  -o $(BASE_DIR)/build/$(APPNAME) -v .

external :
	cd ${BASE_DIR}/cmd && CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build  -gcflags=-trimpath=${PWD} -asmflags=-trimpath=${PWD}   -ldflags ${BUILD_EXTERNAL_FLAG}  -o $(BASE_DIR)/build/$(APPNAME) -v .

mini:
	cd ${BASE_DIR}/cmd && CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build  -gcflags=-trimpath=${PWD} -asmflags=-trimpath=${PWD}   -ldflags ${BUILD_MINI_FLAG}  -o $(BASE_DIR)/build/$(APPNAME) -v .
	# need install upx 
	upx $(BASE_DIR)/build/$(APPNAME)
	
clean:
	rm -rf ${BASE_DIR}/build && go clean -cache

gotool:
	-gofmt -w .

help:
	echo "make - compile go source"
	echo "make gotool - run gofmt"
	echo "make clean - do some clean job"