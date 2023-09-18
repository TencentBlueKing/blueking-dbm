SRV_NAME= redis-dts
binDir=bin

clean:
	-rm ./${binDir}/${SRV_NAME}

build:clean
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build  -o ./${binDir}/$(SRV_NAME) -v main.go


.PHONY: init clean build gotool clean help api curl