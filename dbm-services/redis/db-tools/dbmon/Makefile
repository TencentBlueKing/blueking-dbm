SRV_NAME=bk-dbmon

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./build/$(SRV_NAME) -v main.go

clean:
	rm -rf ./build && go clean -cache


.PHONY: init clean build
