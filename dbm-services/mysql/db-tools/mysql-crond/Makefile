PROJ="mysql-crond"
MODULE="dbm-services/mysql/db-tools/mysql-crond"
VERSION = $(error please set VERSION flag)
#VERSION=$(shell date +'%y%m%d.%H.%M')
PKG=${PROJ}.tar.gz
OUTPUT_DIR=build
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash=`git rev-parse HEAD` "
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash="" "

.PHONY: release-bin
release-bin:
	@CGO_ENABLE=0 GOARCH=amd64 GOOS=linux go build -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}
	@cp mysql-crond.conf.go.tpl $(OUTPUT_DIR)
	@cp start.sh $(OUTPUT_DIR)
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} mysql-crond mysql-crond.conf.go.tpl start.sh

.PHONY: dev-bin
dev-bin:
	@CGO_ENABLE=0 go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}
	@cp mysql-crond.conf.go.tpl $(OUTPUT_DIR)
	@cp start.sh $(OUTPUT_DIR)
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} mysql-crond mysql-crond.conf.go.tpl start.sh

clean:
	@rm -rf ${OUTPUT_DIR}