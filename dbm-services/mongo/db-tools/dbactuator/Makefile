SRV_NAME=mongo-dbactuator

clean:
	-rm ./build/${SRV_NAME}

local:clean
	CGO_ENABLED=0 go build  -o ./build/$(SRV_NAME) -v main.go
build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./build/$(SRV_NAME) -v main.go

.PHONY: init clean build
