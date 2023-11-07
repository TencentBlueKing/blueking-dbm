PROJ="mysql-monitor"
MODULE="dbm-services/mysql/db-tools/mysql-monitor"
VERSION = $(error please set VERSION flag)
GITHASH = ""
PKG = ${PROJ}.tar.gz
OUTPUT_DIR = build
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash=${GITHASH} "
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.buildStamp=`date -u '+%Y-%m-%d_%I:%M:%S%p'` -X ${MODULE}/cmd.gitHash="" "


.PHONY: release-bin
release-bin:
	@CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}
	@cp pt-config-diff ${OUTPUT_DIR}/pt-config-diff
	@cp pt-summary ${OUTPUT_DIR}/pt-summary
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} mysql-monitor pt-config-diff pt-summary

.PHONY: dev-bin
dev-bin:
	@go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	@cp pt-config-diff ${OUTPUT_DIR}/pt-config-diff
	@cp pt-summary ${OUTPUT_DIR}/pt-summary
	@tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PKG} mysql-monitor pt-config-diff pt-summary

.PHONY: clean
clean:
	@rm -rf $(OUTPUT_DIR)


