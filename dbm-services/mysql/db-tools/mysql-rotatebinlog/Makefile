PROJ="mysql-rotatebinlog"
PROJ_BIN="rotatebinlog"
MODULE="dbm-services/mysql/db-tools/mysql-rotatebinlog"
VERSION = $(error please set VERSION flag)
PROJ_PKG = ${PROJ}.tar.gz
OUTPUT_DIR = build
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash=`git rev-parse HEAD` "
BETA_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash="" "
BASE_DIR = $(shell pwd)

.PHONY: build
build:
	@CGO_ENABLE=0 GOARCH=amd64 GOOS=linux go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}/${PROJ_BIN}

.PHONY: release
release: build
	@cp config.example.yaml ${OUTPUT_DIR}/${PROJ}/config.yaml.example
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PROJ_PKG} ${PROJ}/

.PHONY: beta
beta:
	@cd ${BASE_DIR}/cmd && go build -ldflags ${BETA_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}/${PROJ_BIN}
	@cp config.example.yaml ${OUTPUT_DIR}/${PROJ}/config.yaml.example
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PROJ_PKG} ${PROJ}/

.PHONY: clean
clean:
	@rm -rf $(OUTPUT_DIR)


