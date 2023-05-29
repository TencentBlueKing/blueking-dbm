SRV_NAME=bk-dbmon

# default values for BUILD, VERSION and GITHASH
ifneq ($(BUILDSTAMP),)
	BUILDSTAMP := $(BUILDSTAMP)
else
	BUILDSTAMP := $(shell date +%FT%T%z)
endif

ifneq ($(VERSION),)
	VERSION := $(VERSION)
else
	VERSION := 0.0.1
endif

ifneq ($(GITHASH),)
	GITHASH := $(GITHASH)
else
	GITHASH := $(shell git rev-parse --short HEAD)
endif

GOVERSION=$(shell go  env GOVERSION)

MODULE="dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/buildinfo"
BUILD_FLAG = -ldflags "-X '${MODULE}.version=${VERSION}' -X '${MODULE}.githash=${GITHASH}' -X '${MODULE}.buildstamp=${BUILDSTAMP}' -X '${MODULE}.goversion=${GOVERSION}' "
TRIMPATH = -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"
.DEFAULT_GOAL := build

local:
	CGO_ENABLED=0 go build $(TRIMPATH)  -v $(BUILD_FLAG) -o ./build/$(SRV_NAME) -v main.go

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  $(TRIMPATH) -v $(BUILD_FLAG)  -o ./build/$(SRV_NAME) -v main.go

clean:
	rm -rf ./build && go clean -cache


.PHONY: init clean build