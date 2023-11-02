SRV_NAME=bk-dbmon

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./build/$(SRV_NAME) -v main.go

clean:
	-rm ./build/${SRV_NAME}


.PHONY: init clean build
