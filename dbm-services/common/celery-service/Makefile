PROJ="celery-service"
MODULE="dbm-services/common/celery-service"
VERSION=$(error please set VERSION flag)
PKG=${PROJ}.tar.gz
OUTPUT_DIR=build
RELEASE_BUILD_FLAG = "-X main.version=${VERSION} -X main.gitHash=`git rev-parse HEAD` "
DEV_BUILD_FLAG = "-X main.version="develop" -X main.gitHash="" "
BK_NAMESPACE = blueking
BK_DH_URL = mirrors.tencent.com/build

.PHONY: release-bin
release-bin:
	CGO_ENABLED=0 GOARCH=amd64 GOOS=linux go build -ldflags ${RELEASE_BUILD_FLAG} -o ${OUTPUT_DIR}/${$PROJ}
	cp -r collect ${OUTPUT_DIR}
	cp external-tasks.yaml ${OUTPUT_DIR}
	tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PROJ}.tar.gz ${PROJ} external-tasks.yaml collect

.PHONY: dev-bin
dev-bin:
	go build -ldflags ${DEV_BUILD_FLAG} -o ${OUTPUT_DIR}/${PROJ}
	cp -r collect ${OUTPUT_DIR}
	cp external-tasks.yaml ${OUTPUT_DIR}
	tar -C ${OUTPUT_DIR} -zcf ${OUTPUT_DIR}/${PROJ}.tar.gz ${PROJ} external-tasks.yaml collect

.PHONY: bk-image
bk-image: release-bin
	docker build --build-arg SRV_NAME=${PROJ} --rm -t ${BK_DH_URL}/${BK_NAMESPACE}/${PROJ}:${VERSION} .
	docker push ${BK_DH_URL}/${BK_NAMESPACE}/${PROJ}:${VERSION}

.PHONY: clean
clean:
	rm -rf $(OUTPUT_DIR)