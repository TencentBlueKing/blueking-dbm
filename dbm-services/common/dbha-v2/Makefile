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

# services list
SERVICES := admin analysis receiver probe

# define common go build command
define GO_BUILD
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=$(GO_OS) GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) \
				-gcflags="all=-trimpath=$(PWD)" -asmflags="all=-trimpath=$(PWD)" \
				-o $(BUILD_DIR)/$(1) cmd/$(1)/main.go
endef

.PHONY: all proto $(SERVICES) clean format test package help

# package
PKG_DIR   = $(BUILD_DIR)/$(PROJECT)
PKG_NAME  = $(PROJECT).tar.gz

# build target

all: proto admin analysis receiver probe toolkits

proto: $(GO_GEN_FILES)
	@goimports -w .

admin:
	$(call GO_BUILD,$@)

analysis:
	$(call GO_BUILD,$@)

receiver:
	$(call GO_BUILD,$@)

probe:
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
				-asmflags="all=-trimpath=$(PWD)" -o $(BUILD_DIR)/$@ tools/cmd/cluster.go

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
package: $(SERVICES) toolkits
	@echo "Packaging $(PKG_NAME)..."
	@rm -rf $(PKG_DIR)
	@mkdir -p $(PKG_DIR)/etc $(PKG_DIR)/logs $(PKG_DIR)/pids $(PKG_DIR)/toolkits
	@cp $(addprefix $(BUILD_DIR)/,$(SERVICES)) $(PKG_DIR)/
	@cp $(BUILD_DIR)/cluster $(PKG_DIR)/toolkits/
	@-cp etc/*.yaml $(PKG_DIR)/etc/ 2>/dev/null || true
	@cd $(BUILD_DIR) && tar -czvf $(PKG_NAME) $(PROJECT)
	@rm -rf $(PKG_DIR)
	@echo "Package created: $(BUILD_DIR)/$(PKG_NAME)"

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
	@echo "  package    - Create release package ($(PKG_NAME))"
	@echo "  format     - Format code and tidy modules"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean build artifacts"
	@echo "  help       - Show this help message"
