PROJ="mysql-crond"
MODULE="dbm-services/mysql/db-tools/mysql-crond"
VERSION = $(error please set VERSION flag)
GITHASH = ""
GITDATE = ""
TAR_PKG=${PROJ}.tar
PKG=${PROJ}.tar.gz
OUTPUT_DIR=build
RELEASE_BUILD_FLAG = "-X ${MODULE}/cmd.version=${VERSION} -X ${MODULE}/cmd.gitHash=${GITHASH}"
DEV_BUILD_FLAG = "-X ${MODULE}/cmd.version="develop" -X ${MODULE}/cmd.gitHash="" "

.PHONY: build
build:
	CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -gcflags="all=-trimpath=${PWD}" -asmflags="all=-trimpath=${PWD}" -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}

.PHONY: release-bin
release-bin: build
	cp mysql-crond.conf.go.tpl $(OUTPUT_DIR)
	cp start.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/start.sh
	cp mysql_crond_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/mysql_crond_keep_alive.sh
	cp add_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/add_keep_alive.sh
	cp remove_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/remove_keep_alive.sh
	# 为了保证 tar 压缩得到的包的 md5 一致，这里修改文件的时间戳，同时把 tar -zcf 拆为 tar -cf && gzip
	find ${OUTPUT_DIR} -exec touch -t ${GITDATE} {} +
	tar -C ${OUTPUT_DIR} --numeric-owner -cvf ${OUTPUT_DIR}/${TAR_PKG} mysql-crond mysql-crond.conf.go.tpl start.sh mysql_crond_keep_alive.sh add_keep_alive.sh remove_keep_alive.sh
	gzip -n -f ${OUTPUT_DIR}/${TAR_PKG}

.PHONY: dev-bin
dev-bin:
	CGO_ENABLED=0 go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}
	cp mysql-crond.conf.go.tpl $(OUTPUT_DIR)
	cp start.sh $(OUTPUT_DIR)
	cp mysql_crond_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/mysql_crond_keep_alive.sh
	cp add_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/add_keep_alive.sh
	cp remove_keep_alive.sh $(OUTPUT_DIR) && chmod +x $(OUTPUT_DIR)/remove_keep_alive.sh
	tar -C ${OUTPUT_DIR} --numeric-owner -cvf ${OUTPUT_DIR}/${TAR_PKG} mysql-crond mysql-crond.conf.go.tpl start.sh mysql_crond_keep_alive.sh add_keep_alive.sh remove_keep_alive.sh

clean:
	rm -rf ${OUTPUT_DIR} && go clean -cache
