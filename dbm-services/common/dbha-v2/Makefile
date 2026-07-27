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

.PHONY: all proto $(SERVICES) doc toolkits cluster bwmgr clean format test \
        package package-server package-probe help \
        probe-windows package-probe-windows check-windows check-generate

# package
SERVER_PKG_DIR  = $(BUILD_DIR)/$(PROJECT)-server
SERVER_PKG_NAME = $(VERSION)-server.tar.gz
PROBE_PKG_DIR   = $(BUILD_DIR)/$(PROJECT)-probe
PROBE_PKG_NAME  = $(VERSION)-probe.tar.gz
PROBE_WINDOWS_PKG_DIR  = $(BUILD_DIR)/$(PROJECT)-probe-windows
PROBE_WINDOWS_PKG_NAME = $(VERSION)-probe-windows.zip

SERVER_BINS = dbha-admin dbha-analysis dbha-receiver
PROBE_BINS  = dbha-probe
PROBE_WINDOWS_BIN = dbha-probe.exe

# server-side toolkit binaries (keep in sync with scripts/deploy.sh TOOLKIT_FILES)
SERVER_TOOLKITS = dbha-cluster dbha-bwmgr
SERVER_TOOLKIT_CONFIGS = cluster.yaml bwmgr.yaml

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

# Windows probe ships PowerShell scripts only; bash scripts and the bash-only
# guard-utils.sh library are intentionally excluded. render_configs.py is Python
# and cross-platform (fcntl import is guarded), so it is included for config gen.
PROBE_WINDOWS_SCRIPTS = scripts/start-probe.ps1 scripts/stop-probe.ps1 \
                        scripts/start-probe-keepalive.ps1 scripts/stop-probe-keepalive.ps1 \
                        scripts/render_configs.py
# Shared helpers required by start/stop *.ps1 (named-event name derivation).
PROBE_WINDOWS_LIBS = scripts/lib/probe-event-utils.ps1

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

# Windows probe build. GO_BUILD's -o has no .exe suffix, so this is a standalone
# invocation that emits dbha-probe.exe (GOOS pinned to windows regardless of GO_OS).
probe-windows: proto
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) \
				-gcflags="all=-trimpath=$(PWD)" -asmflags="all=-trimpath=$(PWD)" \
				-o $(BUILD_DIR)/$(PROBE_WINDOWS_BIN) cmd/probe/main.go

# Cross-compilation gate: ensures the whole module still builds for Windows.
# CI has no Windows runner, so *_windows_test.go are skipped there; this target is
# the guard that catches Windows-only compile breakage.
check-windows:
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build ./...

# generate swagger api doc with swag
doc:
	@mkdir -p $(BUILD_DIR)
	GOBIN=$(PWD)/$(BUILD_DIR) go install github.com/swaggo/swag/v2/cmd/swag@latest
	$(BUILD_DIR)/swag fmt
	$(BUILD_DIR)/swag init -g cmd/admin/main.go --parseDependency --parseDepth 3


toolkits: cluster bwmgr

# test toolkits build target
cluster:
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=${GO_OS} GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) -gcflags="all=-trimpath=$(PWD)" \
				-asmflags="all=-trimpath=$(PWD)" -o $(BUILD_DIR)/$(BIN_PREFIX)$@ ./tools/cmd/cluster

# black-white list manager toolkit
bwmgr:
	@mkdir -p $(BUILD_DIR)
	CGO_ENABLED=0 GOOS=${GO_OS} GOARCH=amd64 go build -ldflags=$(BUILD_FLAG) -gcflags="all=-trimpath=$(PWD)" \
				-asmflags="all=-trimpath=$(PWD)" -o $(BUILD_DIR)/$(BIN_PREFIX)$@ ./tools/cmd/bwmgr

# build protobuf to go
$(GEN_DIR)/%.pb.go: $(PROTO_DIR)/%.proto
	@mkdir -p $(GEN_DIR)
	$(PROTOC) $(GO_FLAGS) -I$(PROTO_DIR) $<

format:
	@goimports -w . && find . -name go.mod -execdir go mod tidy \;

# run tests
test: check-generate
	go test -v -race -cover ./...

# ensure provider aggregate blank-imports are up to date with manifest.go
# Fail on working-tree drift vs index OR untracked files under all* (staged-but-uncommitted is OK).
check-generate:
	CGO_ENABLED=0 go generate ./internal/provider/...
	@if ! git diff --quiet -- 'internal/provider/all*' || \
		[ -n "$$(git ls-files --others --exclude-standard -- 'internal/provider/all*')" ]; then \
		echo "provider aggregates out of date; run: go generate ./internal/provider/..."; \
		git status --porcelain -- 'internal/provider/all*'; \
		exit 1; \
	fi

# build and package
package: package-server package-probe package-probe-windows

# server package: admin/analysis/receiver + toolkits + server-side scripts/configs
package-server: admin analysis receiver toolkits
	@echo "Packaging $(SERVER_PKG_NAME)..."
	@rm -rf $(SERVER_PKG_DIR)
	@mkdir -p $(SERVER_PKG_DIR)/bin $(SERVER_PKG_DIR)/etc \
		$(SERVER_PKG_DIR)/logs $(SERVER_PKG_DIR)/pids \
		$(SERVER_PKG_DIR)/toolkits
	@cp $(addprefix $(BUILD_DIR)/,$(SERVER_BINS)) $(SERVER_PKG_DIR)/bin/
	@cp $(addprefix $(BUILD_DIR)/,$(SERVER_TOOLKITS)) $(SERVER_PKG_DIR)/toolkits/
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
	@cp $(addprefix etc/,$(SERVER_TOOLKIT_CONFIGS)) $(SERVER_PKG_DIR)/etc/
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

# windows probe package: dbha-probe.exe + PowerShell scripts + render_configs.py
# + probe templates/rc; deliberately excludes bash scripts and guard-utils.sh.
package-probe-windows: probe-windows
	@command -v zip >/dev/null 2>&1 || { echo "ERROR: 'zip' is required for package-probe-windows"; exit 1; }
	@echo "Packaging $(PROBE_WINDOWS_PKG_NAME)..."
	@rm -rf $(PROBE_WINDOWS_PKG_DIR)
	@mkdir -p $(PROBE_WINDOWS_PKG_DIR)/bin $(PROBE_WINDOWS_PKG_DIR)/etc \
		$(PROBE_WINDOWS_PKG_DIR)/logs $(PROBE_WINDOWS_PKG_DIR)/pids
	@cp $(BUILD_DIR)/$(PROBE_WINDOWS_BIN) $(PROBE_WINDOWS_PKG_DIR)/bin/
	@cp $(PROBE_WINDOWS_SCRIPTS) $(PROBE_WINDOWS_PKG_DIR)/
	@mkdir -p $(PROBE_WINDOWS_PKG_DIR)/lib
	@cp $(PROBE_WINDOWS_LIBS) $(PROBE_WINDOWS_PKG_DIR)/lib/
	@mkdir -p $(PROBE_WINDOWS_PKG_DIR)/etc/templates/snippets
	@cp $(addprefix etc/templates/,$(PROBE_TEMPLATES)) \
		$(PROBE_WINDOWS_PKG_DIR)/etc/templates/
	@cp $(addprefix etc/templates/snippets/,$(PROBE_SNIPPETS)) \
		$(PROBE_WINDOWS_PKG_DIR)/etc/templates/snippets/
	@cp etc/dbha-v2.probe.rc.example \
		$(PROBE_WINDOWS_PKG_DIR)/etc/dbha-v2.probe.rc.example
	@cd $(BUILD_DIR) && zip -r $(PROBE_WINDOWS_PKG_NAME) $(PROJECT)-probe-windows >/dev/null
	@rm -rf $(PROBE_WINDOWS_PKG_DIR)
	@echo "Package created: $(BUILD_DIR)/$(PROBE_WINDOWS_PKG_NAME)"

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
	@echo "  probe-windows  - Build Windows probe binary (dbha-probe.exe)"
	@echo "  check-windows  - Cross-compile the whole module for Windows (build gate)"
	@echo "  toolkits   - Build toolkit binaries (cluster, bwmgr)"
	@echo "  cluster    - Build cluster toolkit (dbha-cluster)"
	@echo "  bwmgr      - Build black-white list manager (dbha-bwmgr)"
	@echo "  package    - Build and create both server and probe release packages"
	@echo "  package-server - Create server release package (services + toolkits + etc templates)"
	@echo "  package-probe  - Create probe release package ($(VERSION)-probe.tar.gz)"
	@echo "  package-probe-windows - Create Windows probe release package ($(VERSION)-probe-windows.zip)"
	@echo "  format     - Format code and tidy modules"
	@echo "  test       - Run tests"
	@echo "  check-generate - Regenerate provider aggregates and fail if dirty"
	@echo "  clean      - Clean build artifacts"
	@echo "  help       - Show this help message"
