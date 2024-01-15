SRV_NAME=mongo-dbactuator

clean:
	-rm ./bin/${SRV_NAME}

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./bin/$(SRV_NAME) -v main.go

.PHONY: init clean build
