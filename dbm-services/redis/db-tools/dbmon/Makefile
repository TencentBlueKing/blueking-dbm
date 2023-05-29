SRV_NAME=bk-dbmon

clean:
	-rm ./bin/${SRV_NAME}

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./bin/$(SRV_NAME) -v main.go


LOCAL_PKG_DIR := $(shell eval "./bin/bk-dbmon -v|awk '{print $2}'")
version:=$(shell sh -c "./bin/bk-dbmon -v|awk '{print $1}'")

package:build
	mkdir -p bkdbmon
	cp ./bin/$(SRV_NAME) ./bkdbmon/
	cp ./start.sh ./bkdbmon/
	cp ./stop.sh ./bkdbmon/
	cp ./dbmon-config.yaml ./bkdbmon/

version:build
	@echo LOCAL_PKG_DIR=$(LOCAL_PKG_DIR)
	@echo version=$(version)

.PHONY: init clean build
