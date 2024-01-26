SRV_NAME=mongo-dbactuator

BUILD_FLAG = -ldflags "-X '${MODULE}.version=${VERSION}' -X '${MODULE}.githash=${GITHASH}' -X '${MODULE}.buildstamp=`date +%FT%T%z`' -X '${MODULE}.goversion=${GOVERSION}' "
TRIMPATH = -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}"

clean:
	-rm ./build/${SRV_NAME}

local:clean
	CGO_ENABLED=0 go build  $(TRIMPATH) -v $(BUILD_FLAG)   -o ./build/$(SRV_NAME) -v main.go
build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build   $(TRIMPATH) -v $(BUILD_FLAG)   -o ./build/$(SRV_NAME) -v main.go

.PHONY: init clean build
