SHELL := /bin/bash
BASEDIR = $(shell pwd)
SRV_NAME = dbpartition
COMMAND_NAME = partition
VER = latest
CURRENT_VERSION = $(VER)
TEST_VERSION = test-$(VER)
export GOOS = linux
BUILD_PATH = .
OUTPUT_DIR = build
OUTPUT_BIN = $(OUTPUT_DIR)/$(COMMAND_NAME)

all: build
api:
	mkdir -p $(OUTPUT_DIR)
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -o $(OUTPUT_BIN) -v ${BUILD_PATH}
build:
	mkdir -p $(OUTPUT_DIR)
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -o $(OUTPUT_BIN) -v ${BUILD_PATH}

publish:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(CURRENT_VERSION) .

test:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .

test_mac:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .

clean:
	rm -rf $(OUTPUT_DIR)

curl:
	echo curl -XGET -H "Content-Type: application/json" http://127.0.0.1:8080/user
help:
	echo "make - compile go source"
	echo "make gotool - run gofmt & go too vet"
	echo "make clean - do some clean job"

.PHONY: all build api publish test test_mac gotool clean help curl