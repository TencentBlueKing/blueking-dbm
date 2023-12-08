PROJ="mysql-rotatebinlog"
PROJ_BIN="rotatebinlog"
MODULE="dbm-services/mysql/db-tools/mysql-rotatebinlog"
VERSION = $(error please set VERSION flag)
GITHASH=""
GITDATE=""
TAR_PKG = ${PROJ}.tar
PROJ_PKG = ${PROJ}.tar.gz
OUTPUT_DIR = build
RELEASE_BUILD_FLAG = "-w -s -X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.gitHash=${GITHASH} "
BETA_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.gitHash="" "
BASE_DIR = $(shell pwd)

.PHONY: build
build:
	CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}/${PROJ_BIN}

.PHONY: release-bin
release-bin: build
	cp config.example.yaml ${OUTPUT_DIR}/${PROJ}/config.yaml.example
	# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
	find ${OUTPUT_DIR} -exec touch -t ${GITDATE} {} +
	tar -C ${OUTPUT_DIR} -cf ${OUTPUT_DIR}/${TAR_PKG} ${PROJ}/
	gzip -n -f ${OUTPUT_DIR}/${TAR_PKG}

.PHONY: beta
beta:
	cd ${BASE_DIR}/cmd && go build -ldflags ${BETA_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}/${PROJ_BIN}
	cp config.example.yaml ${OUTPUT_DIR}/${PROJ}/config.yaml.example
	tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PROJ_PKG} ${PROJ}/

.PHONY: clean
clean:
	rm -rf $(OUTPUT_DIR) && go clean -cache


