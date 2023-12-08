PROJ="mysql-monitor"
MODULE="dbm-services/mysql/db-tools/mysql-monitor"
VERSION = $(error please set VERSION flag)
GITHASH = ""
GITDATE = ""
TAR_PKG = ${PROJ}.tar
PKG = ${PROJ}.tar.gz
OUTPUT_DIR = build
RELEASE_BUILD_FLAG = "-w -s -X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.gitHash=${GITHASH} "
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.gitHash="" "

.PHONY: build
build:
	CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}

.PHONY: release-bin
release-bin: build
	cp pt-config-diff ${OUTPUT_DIR}/pt-config-diff
	cp pt-summary ${OUTPUT_DIR}/pt-summary
	# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
	find ${OUTPUT_DIR} -exec touch -t ${GITDATE} {} +
	tar -C ${OUTPUT_DIR} --numeric-owner -cvf ${OUTPUT_DIR}/${TAR_PKG} ${PROJ} mysql-monitor pt-config-diff pt-summary
	gzip -n -f ${OUTPUT_DIR}/${TAR_PKG}

.PHONY: dev-bin
dev-bin:
	go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	cp pt-config-diff ${OUTPUT_DIR}/pt-config-diff
	cp pt-summary ${OUTPUT_DIR}/pt-summary
	tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} mysql-monitor pt-config-diff pt-summary

.PHONY: clean
clean:
	rm -rf $(OUTPUT_DIR) && go clean -cache
