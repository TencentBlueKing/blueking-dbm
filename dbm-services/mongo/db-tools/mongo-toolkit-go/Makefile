export GO111MODULE=on
backup:= mongo_backup
recover:= mongo_recover
idc:= idc_mongo_backup
once:= once_mongo_backup
toolkit:= mongo-toolkit-go
bscli:=bs-cli
OS:= $(shell uname -s)

VERSION=$(shell cat VERSION)
BUILD=$(shell date +%FT%T%z)
COMMIT_SHA1=`git rev-parse --short HEAD`
GO_VERSION=$(shell go version)


LDFLAGS=-ldflags "-X 'main.VERSION=${VERSION}' -X 'main.BuildDate=${BUILD}' -X 'main.CommitSha1=${COMMIT_SHA1}' -X 'main.GoVersion=${GO_VERSION}'"


all: check build
	@echo "all"
check:
	@echo "  >  Check by golangci-lint..."
	golangci-lint run cmd/bscli/main.go
	golangci-lint run cmd/mongo-toolkit-go/main.go
build:
	@echo "  >  Building $(OS) binary..."
	go build -v $(LDFLAGS) -o target/$(toolkit)_$(OS) cmd/mongo-toolkit-go/main.go
	# go build -o target/$(bscli)_$(OS) cmd/bscli/main.go


linux:
	@echo "  >  Building linux binary..."
	# GOOS=linux GOARCH=amd64 go build -o target/$(bscli)_Linux cmd/bscli/main.go
	GOOS=linux GOARCH=amd64 go build -v $(LDFLAGS) -o target/$(toolkit)_Linux cmd/mongo-toolkit-go/main.go
