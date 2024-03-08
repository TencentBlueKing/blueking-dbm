SRV_NAME=mongo-dbactuator
# default values for BUILD, VERSION and GITHASH
ifneq ($(BUILD),)
	BUILD := $(shell date +%FT%T%z)
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
BUILD_FLAG = -ldflags "-X '${MODULE}.version=${VERSION}' -X '${MODULE}.githash=${GITHASH}' -X '${MODULE}.buildstamp=`date +%FT%T%z`' -X '${MODULE}.goversion=${GOVERSION}' "
TRIMPATH = -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"
.DEFAULT_GOAL := build

clean:
ifneq (,$(wildcard ./build/${SRV_NAME}))
	-rm ./build/${SRV_NAME}
endif


local:clean
	CGO_ENABLED=0 go build  $(TRIMPATH) -v $(BUILD_FLAG) -o ./build/$(SRV_NAME) -v main.go

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build $(TRIMPATH) -v $(BUILD_FLAG) -o ./build/$(SRV_NAME) -v main.go

.PHONY: init clean build
