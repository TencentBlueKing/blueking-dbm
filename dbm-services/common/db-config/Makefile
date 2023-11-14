SHELL := /bin/bash
BASEDIR = $(shell pwd)
SRV_NAME = dbconfig
CLI_NAME = bkconfigcli
SRV_NAME_CMD = bkconfigsvr
CLI_NAME_CMD = bkconfigcli
VER = 0.0.1
ALPHA_VERSION = $(VER)-alpha.3
CURRENT_VERSION = release-$(VER)
TEST_VERSION = test-$(VER)
NAMESPACE = blueking
DH_URL = mirrors.tencent.com
export GOOS ?= linux
CMD_HOME = bk-dbconfig/cmd/
MODULE="dbm-services/common/db-config"
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.gitHash=${GITHASH} "
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.gitHash="" "

all: build

client:
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -ldflags ${RELEASE_BUILD_FLAG} -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -o ./$(CLI_NAME_CMD) -v ${CMD_HOME}/${CLI_NAME_CMD}
server:
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=amd64 go build -ldflags ${RELEASE_BUILD_FLAG} -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -o ./$(SRV_NAME_CMD) -v ${CMD_HOME}/${SRV_NAME_CMD}

build:clean client server

publish:build
	docker build --build-arg SRV_NAME=$(SRV_NAME) --rm -t $(SRV_NAME):$(CURRENT_VERSION) .
	docker tag $(SRV_NAME):$(CURRENT_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(CURRENT_VERSION)

test:build
	docker build --build-arg SRV_NAME=$(SRV_NAME) --rm -t $(SRV_NAME):$(TEST_VERSION) .
	docker tag $(SRV_NAME):$(TEST_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(TEST_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(TEST_VERSION)

alpha:build
	docker build --build-arg SRV_NAME=$(SRV_NAME) --rm -t $(SRV_NAME):$(ALPHA_VERSION) .
	docker tag $(SRV_NAME):$(ALPHA_VERSION) $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(ALPHA_VERSION)
	docker push $(DH_URL)/${NAMESPACE}/$(SRV_NAME):$(ALPHA_VERSION)

usql:
	git clone

gotool:
	-gofmt -w .
	-go tool vet . 2>&1 | grep -v vendor;true
clean:
	rm -f ${SRV_NAME_CMD} ${CLI_NAME_CMD}
curl:
	echo curl -XGET -H "Content-Type: application/json" http://127.0.0.1:8080/user
help:
	echo "make - compile go source"
	echo "make gotool - run gofmt & go too vet"
	echo "make clean - do some clean job"

.PHONY: all gotool clean help api curl