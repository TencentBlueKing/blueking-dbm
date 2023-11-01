PROJ="mysql-table-checksum"
MODULE="dbm-services/mysql/db-tools/mysql-table-checksum"
VERSION = $(error please set VERSION flag)
PKG="mysql-checksum.tar.gz" # 这是个不太好改的错误了
OUTPUT_DIR=build
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash=`git rev-parse HEAD` "
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash="" "

.PHONY: release-bin
release-bin:
	@CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	@chmod +x pt-table-checksum pt-table-sync
	@cp -a pt-table-checksum ${OUTPUT_DIR}/
	@cp -a pt-table-sync ${OUTPUT_DIR}/
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} ${PROJ} pt-table-checksum pt-table-sync

.PHONY: dev-bin
dev-bin:
	@go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	@cp pt-table-checksum ${OUTPUT_DIR}/
	@cp pt-table-sync ${OUTPUT_DIR}/
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} ${PROJ} pt-table-checksum pt-table-sync

.PHONY: clean
clean:
	@rm -rf ${OUTPUT_DIR}