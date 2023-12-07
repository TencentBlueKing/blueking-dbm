SHELL := /bin/bash
BASEDIR = $(shell pwd)
SRV_NAME = privservice
COMMAND_NAME = privservice
VER = latest
CURRENT_VERSION = release-$(VER)
TEST_VERSION = test-$(VER)
export GOOS = linux
BUILD_PATH = .

all: build
api:
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -o $(COMMAND_NAME)  -v ${BUILD_PATH}
build:clean
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -o $(COMMAND_NAME) -v ${BUILD_PATH}

publish:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(CURRENT_VERSION) .

test:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .

test_mac:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .

curl:
	echo curl -XGET -H "Content-Type: application/json" http://127.0.0.1:8080/user
help:
	echo "make - compile go source"
	echo "make gotool - run gofmt & go too vet"
	echo "make clean - do some clean job"

.PHONY: all gotool clean help api curl
