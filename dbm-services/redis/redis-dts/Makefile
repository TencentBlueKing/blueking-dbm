SRV_NAME= redis_dts_server

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./build/$(SRV_NAME) -v main.go

clean:
	-rm ./build/${SRV_NAME}

.PHONY: init clean build gotool clean help api curl