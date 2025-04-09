PROJ="bkdata-kafka-consumer"
PKG=$(PROJ).tgz
OUTPUT_DIR=build

all:
	@CGO_ENABLE=0 GOOS=linux GOARCH=amd64 go build -o $(OUTPUT_DIR)/$(PROJ)

clean:
	@rm -rf $(OUTPUT_DIR)