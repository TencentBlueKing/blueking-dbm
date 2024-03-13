export GO111MODULE=on
SRV_NAME:= mongo-toolkit-go
bscli:=bs-cli
OS:= $(shell uname -s)

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


LDFLAGS=-ldflags "-X 'main.VERSION=${VERSION}' -X 'main.BuildDate=${BUILD}' -X 'main.CommitSha1=${COMMIT_SHA1}' -X 'main.GoVersion=${GO_VERSION}'"
all: check build
	@echo "all"
check:
	@echo "  >  Check by golangci-lint..."
	golangci-lint run cmd/bscli/main.go
	golangci-lint run cmd/mongo-toolkit-go/main.go

build:
	@echo "  >  Building Linux binary..."
	# go build -v $(LDFLAGS) -o target/$(toolkit)_$(OS) cmd/mongo-toolkit-go/main.go
	GOOS=linux GOARCH=amd64 go build $(TRIMPATH) -v $(BUILD_FLAG) -o ./build/$(SRV_NAME)_Linux cmd/$(SRV_NAME)/main.go

local:
	@echo "  >  Building $(OS)  binary..."
	go build -v $(LDFLAGS) -o target/$(toolkit) cmd/mongo-toolkit-go/main.go