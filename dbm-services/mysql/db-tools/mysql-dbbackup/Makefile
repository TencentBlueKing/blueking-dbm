PROJ_BIN="dbbackup"
PROJ="dbbackup-go"
OUTPUT_DIR = build
PKG_DIR=${OUTPUT_DIR}/${PROJ}
PROJ_PKG=${PROJ}.tar.gz

.PHONY: build
build:
	@echo "Building ${OUTPUT_DIR}/${PROJ_BIN}"
	@mkdir -p ${OUTPUT_DIR}
	@GOOS=linux GOARCH=amd64 go build -o ${OUTPUT_DIR}/${PROJ_BIN}

.PHONY: package
package:
	@echo "Building ${OUTPUT_DIR}/${PROJ_BIN}"
	@GOOS=linux GOARCH=amd64 go build -o ${OUTPUT_DIR}/${PROJ_BIN}
	@echo "Packaging ${PROJ_PKG}"
	@mkdir -p ${PKG_DIR}
	@cp ${OUTPUT_DIR}/${PROJ_BIN} ${PKG_DIR}/ && cp dbbackup_main.sh ${PKG_DIR}/
	@cp -r dbbackup-go-deps/* ${PKG_DIR}
	@chmod +x ${PKG_DIR}/*.sh && chmod +x ${PKG_DIR}/dbbackup
	@chmod +x ${PKG_DIR}/bin/* && chmod +x ${PKG_DIR}/bin/*/*
	@cp mydumper_for_tdbctl.cnf ${PKG_DIR}
	@tar -C ${OUTPUT_DIR} -zcvf ${OUTPUT_DIR}/${PROJ_PKG} ${PROJ}

.PHONY: clean
clean:
	@rm -rf ${OUTPUT_DIR}
	@rm -rf ${PROJ}




