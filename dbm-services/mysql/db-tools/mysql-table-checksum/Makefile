PROJ="mysql-table-checksum"
MODULE="dbm-services/mysql/db-tools/mysql-table-checksum"
VERSION = $(error please set VERSION flag)
GITHASH=""
# 注意这里的最终产物是 mysql-checksum.tar.gz，不要修改了
TAR_PKG="mysql-checksum.tar"
PKG="mysql-checksum.tar.gz"
OUTPUT_DIR=build
RELEASE_BUILD_FLAG="-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.gitHash=${GITHASH} "
DEV_BUILD_FLAG="-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.gitHash="" "

.PHONY: release-bin
release-bin:
	CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	chmod +x pt-table-checksum pt-table-sync
	cp -a {pt-table-checksum,pt-table-sync} ${OUTPUT_DIR}/
	# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
	find ${OUTPUT_DIR} -exec touch -t 202301010000 {} +
	tar -C ${OUTPUT_DIR} --numeric-owner -cvf ${OUTPUT_DIR}/${TAR_PKG} ${PROJ} pt-table-checksum pt-table-sync
	gzip -n -f ${OUTPUT_DIR}/${TAR_PKG}

.PHONY: dev-bin
dev-bin:
	go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	cp pt-table-checksum ${OUTPUT_DIR}/
	cp pt-table-sync ${OUTPUT_DIR}/
	tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} ${PROJ} pt-table-checksum pt-table-sync

.PHONY: clean
clean:
	rm -rf ${OUTPUT_DIR} && go clean -cache
