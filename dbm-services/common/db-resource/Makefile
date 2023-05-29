SHELL := /bin/bash
BASEDIR = $(shell pwd)

SRV_NAME = db-resource
COMMAND_NAME = db-resource
VER = v0.0.1
CURRENT_VERSION = release-$(VER)
TEST_VERSION = test-$(VER)
NAMESPACE = sccmsp
DH_URL = mirrors.tencent.com
BUILD_FLAG = "-X main.version=${VER} -X main.buildstamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X main.githash=`git rev-parse HEAD` "
all: build
api:
	go build  -gcflags=-trimpath=${PWD} -asmflags=-trimpath=${PWD} -ldflags ${BUILD_FLAG}    -o bkdbrms  -v .

build:clean
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -gcflags=-trimpath=${PWD} -asmflags=-trimpath=${PWD}  -ldflags ${BUILD_FLAG}  -o $(COMMAND_NAME) -v .

publish:build
	docker build  --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(CURRENT_VERSION) .
	docker tag $(SRV_NAME):$(CURRENT_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)

latest:build
	docker build  --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):latest .
	docker tag $(SRV_NAME):latest $(DH_URL)/${NAMESPACE}/$(SRV_NAME):latest
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):latest

test:build
	docker build --build-arg SRV_NAME=$(COMMAND_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .
	docker tag $(SRV_NAME):$(TEST_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(TEST_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(TEST_VERSION)

gotool:
	@-gofmt -w  .
	@-go tool vet . 2>&1 | grep -v vendor;true
clean:
	# find . -name "[._]*.s[a-w][a-z]" | xargs -i rm -f {}
	rm -f bkdbrms
help:
	@echo "make - compile go source"
	@echo "make gotool - run gofmt & go too vet"
	@echo "make clean - do some clean job"

.PHONY: all gotool clean help api curl
