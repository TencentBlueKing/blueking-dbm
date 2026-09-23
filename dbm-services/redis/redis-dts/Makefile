SRV_NAME= redis_dts_server
BUILD_DATE = $(shell date -u +%Y-%m-%dT%H:%M:%SZ)

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "-X 'main.BuildDate=$(BUILD_DATE)'" -o ./build/$(SRV_NAME) -v main.go

clean:
	-rm ./build/${SRV_NAME}

.PHONY: init clean build gotool clean help api curl