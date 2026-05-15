#
# MIT License
#
# Copyright (c) 2023 腾讯蓝鲸
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# base
PROJECT  := dbha-v2
PROTOC    = protoc
PROTO_DIR = pkg/proto/idl
GEN_DIR   = pkg/proto
BUILD_DIR = build
GO_OS    ?= linux
MODULE    = dbm-services/common/dbha-v2/pkg

# version
BUILDTIME  = $(shell date +%Y-%m-%dT%T%z)
GITTAG     = $(shell git describe --tags --always)
GITHASH    = $(shell git rev-parse --short HEAD)
VERSION   ?= $(GITTAG)-$(shell date +%y.%m.%d)
BUILD_FLAG = "-X '$(MODULE)/version.buildTime=$(BUILDTIME)' \
			 -X '$(MODULE)/version.gitTag=$(GITTAG)' \
			 -X '$(MODULE)/version.gitHash=$(GITHASH)' \
             -X '$(MODULE)/version.version=$(VERSION)' "

# flags
GO_FLAGS = --go_out=$(GEN_DIR) --go_opt=paths=source_relative --go-grpc_out=$(GEN_DIR) --go-grpc_opt=paths=source_relative

# search .proto file
PROTO_FILES = $(wildcard $(PROTO_DIR)/*.proto)

# generate go code files
GO_GEN_FILES=$(PROTO_FILES:$(PROTO_DIR)/%.proto=$(GEN_DIR)/%.pb.go)

# services list and binary names with dbha- prefix
SERVICES   := admin analysis receiver probe
BIN_PREFIX := dbha-
BINARIES   := $(addprefix $(BIN_PREFIX),$(SERVICES))

# define common go build command
define GO_BUILD
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=$(GO_OS) GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) \
				-gcflags="all=-trimpath=$(PWD)" -asmflags="all=-trimpath=$(PWD)" \
				-o $(BUILD_DIR)/$(BIN_PREFIX)$(1) cmd/$(1)/main.go
endef

.PHONY: all proto $(SERVICES) doc toolkits cluster clean format test \
        package package-server package-probe help

# package
SERVER_PKG_DIR  = $(BUILD_DIR)/$(PROJECT)-server
SERVER_PKG_NAME = $(VERSION)-server.tar.gz
PROBE_PKG_DIR   = $(BUILD_DIR)/$(PROJECT)-probe
PROBE_PKG_NAME  = $(VERSION)-probe.tar.gz

SERVER_BINS = dbha-admin dbha-analysis dbha-receiver
PROBE_BINS  = dbha-probe

# per-module template/snippet files (relative to etc/templates and
# etc/templates/snippets respectively)
SERVER_TEMPLATES = admin.yaml analysis.yaml receiver.yaml
SERVER_SNIPPETS  = receiver_source_probe.yaml receiver_source_kafka.yaml \
                   receiver_sink_mysql.yaml
PROBE_TEMPLATES  = probe.yaml
PROBE_SNIPPETS   = probe_mysql_shard.yaml probe_redis_shard.yaml

GUARD_UTILS_LIB = scripts/lib/guard-utils.sh
SERVER_SCRIPTS  = scripts/setup.sh scripts/start-server.sh scripts/stop-server.sh \
                  scripts/deploy.sh scripts/render_configs.py
PROBE_SCRIPTS   = scripts/start-probe.sh scripts/stop-probe.sh \
                  scripts/start-probe-keepalive.sh scripts/stop-probe-keepalive.sh \
                  scripts/deploy.sh scripts/render_configs.py

# build target

all: proto admin analysis receiver probe toolkits

proto: $(GO_GEN_FILES)
	@goimports -w $(GEN_DIR)/*.go

admin: proto
	$(call GO_BUILD,$@)

analysis: proto
	$(call GO_BUILD,$@)

receiver: proto
	$(call GO_BUILD,$@)

probe: proto
	$(call GO_BUILD,$@)

# generate swagger api doc with swag
doc:
	@mkdir -p $(BUILD_DIR)
	GOBIN=$(PWD)/$(BUILD_DIR) go install github.com/swaggo/swag/v2/cmd/swag@latest
	$(BUILD_DIR)/swag fmt
	$(BUILD_DIR)/swag init -g cmd/admin/main.go --parseDependency --parseDepth 3


toolkits: cluster

# test toolkits build target
cluster:
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=${GO_OS} GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) -gcflags="all=-trimpath=$(PWD)" \
				-asmflags="all=-trimpath=$(PWD)" -o $(BUILD_DIR)/$(BIN_PREFIX)$@ tools/cmd/cluster.go

# build protobuf to go
$(GEN_DIR)/%.pb.go: $(PROTO_DIR)/%.proto
	@mkdir -p $(GEN_DIR)
	$(PROTOC) $(GO_FLAGS) -I$(PROTO_DIR) $<

format:
	@goimports -w . && find . -name go.mod -execdir go mod tidy \;

# run tests
test:
	go test -v -race -cover ./...

# build and package
package: package-server package-probe

# server package: admin/analysis/receiver + toolkits + server-side scripts/configs
package-server: admin analysis receiver toolkits
	@echo "Packaging $(SERVER_PKG_NAME)..."
	@rm -rf $(SERVER_PKG_DIR)
	@mkdir -p $(SERVER_PKG_DIR)/bin $(SERVER_PKG_DIR)/etc \
		$(SERVER_PKG_DIR)/logs $(SERVER_PKG_DIR)/pids \
		$(SERVER_PKG_DIR)/toolkits
	@cp $(addprefix $(BUILD_DIR)/,$(SERVER_BINS)) $(SERVER_PKG_DIR)/bin/
	@cp $(BUILD_DIR)/$(BIN_PREFIX)cluster $(SERVER_PKG_DIR)/toolkits/
	@cp $(SERVER_SCRIPTS) $(SERVER_PKG_DIR)/
	@chmod +x $(SERVER_PKG_DIR)/render_configs.py
	@mkdir -p $(SERVER_PKG_DIR)/lib
	@cp $(GUARD_UTILS_LIB) $(SERVER_PKG_DIR)/lib/
	@chmod +x $(SERVER_PKG_DIR)/lib/guard-utils.sh
	@mkdir -p $(SERVER_PKG_DIR)/etc/templates/snippets
	@cp $(addprefix etc/templates/,$(SERVER_TEMPLATES)) \
		$(SERVER_PKG_DIR)/etc/templates/
	@cp $(addprefix etc/templates/snippets/,$(SERVER_SNIPPETS)) \
		$(SERVER_PKG_DIR)/etc/templates/snippets/
	@cp etc/dbha-v2.server.rc.example \
		$(SERVER_PKG_DIR)/etc/dbha-v2.server.rc.example
	@sed -i 's/__VERSION__/$(VERSION)/g' $(SERVER_PKG_DIR)/setup.sh
	@cd $(BUILD_DIR) && tar -czf $(SERVER_PKG_NAME) $(PROJECT)-server
	@rm -rf $(SERVER_PKG_DIR)
	@echo "Package created: $(BUILD_DIR)/$(SERVER_PKG_NAME)"

# probe package: probe binary + probe-side scripts/configs only
package-probe: probe
	@echo "Packaging $(PROBE_PKG_NAME)..."
	@rm -rf $(PROBE_PKG_DIR)
	@mkdir -p $(PROBE_PKG_DIR)/bin $(PROBE_PKG_DIR)/etc \
		$(PROBE_PKG_DIR)/logs $(PROBE_PKG_DIR)/pids
	@cp $(addprefix $(BUILD_DIR)/,$(PROBE_BINS)) $(PROBE_PKG_DIR)/bin/
	@cp $(PROBE_SCRIPTS) $(PROBE_PKG_DIR)/
	@chmod +x $(PROBE_PKG_DIR)/render_configs.py
	@mkdir -p $(PROBE_PKG_DIR)/lib
	@cp $(GUARD_UTILS_LIB) $(PROBE_PKG_DIR)/lib/
	@chmod +x $(PROBE_PKG_DIR)/lib/guard-utils.sh
	@mkdir -p $(PROBE_PKG_DIR)/etc/templates/snippets
	@cp $(addprefix etc/templates/,$(PROBE_TEMPLATES)) \
		$(PROBE_PKG_DIR)/etc/templates/
	@cp $(addprefix etc/templates/snippets/,$(PROBE_SNIPPETS)) \
		$(PROBE_PKG_DIR)/etc/templates/snippets/
	@cp etc/dbha-v2.probe.rc.example \
		$(PROBE_PKG_DIR)/etc/dbha-v2.probe.rc.example
	@cd $(BUILD_DIR) && tar -czf $(PROBE_PKG_NAME) $(PROJECT)-probe
	@rm -rf $(PROBE_PKG_DIR)
	@echo "Package created: $(BUILD_DIR)/$(PROBE_PKG_NAME)"

clean:
	rm -rf $(GEN_DIR)/*.go
	rm -rf $(BUILD_DIR)/*

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all        - Build all services and toolkits (default)"
	@echo "  proto      - Generate protobuf files"
	@echo "  admin      - Build admin service"
	@echo "  analysis   - Build analysis service"
	@echo "  receiver   - Build receiver service"
	@echo "  probe      - Build probe service"
	@echo "  toolkits   - Build toolkit binaries"
	@echo "  package    - Build and create both server and probe release packages"
	@echo "  package-server - Create server release package ($(VERSION)-server.tar.gz)"
	@echo "  package-probe  - Create probe release package ($(VERSION)-probe.tar.gz)"
	@echo "  format     - Format code and tidy modules"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean build artifacts"
	@echo "  help       - Show this help message"
