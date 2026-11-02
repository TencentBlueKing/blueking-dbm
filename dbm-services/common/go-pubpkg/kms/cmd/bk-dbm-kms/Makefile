SRV_NAME = bk-dbm-kms

clean:
	-rm -f build/$(SRV_NAME)

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags "-s -w" -o build/$(SRV_NAME) .

test:
	go test ./...

.PHONY: clean build test
