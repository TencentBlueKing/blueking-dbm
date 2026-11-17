# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

DBHA v2 (Database High Availability v2) is a Go service for database high availability monitoring and failover. It consists of 4 microservices that work together to probe database instances, detect failures, and execute switchover operations.

**Module**: `dbm-services/common/dbha-v2`
**Go Version**: 1.26.0
**License**: MIT

## Build Commands

```bash
# Build all services and toolkits
make all

# Build individual services
make admin      # Build dbha-admin
make analysis   # Build dbha-analysis
make receiver   # Build dbha-receiver
make probe      # Build dbha-probe

# Generate protobuf files (required before building)
make proto

# Build toolkit binaries
make toolkits   # Builds dbha-cluster and dbha-bwmgr

# Format code and tidy modules
make format

# Clean build artifacts
make clean

# Create release packages
make package              # Build server, probe and probe-windows packages
make package-server       # Create server package (services + toolkits + etc templates)
make package-probe        # Create probe package
```

## Testing

```bash
# Run all tests
make test
# Runs `make check-generate` first, then: go test -v -race -cover ./...

# Run tests for a specific package
go test -v -race -cover ./pkg/discovery/...
go test -v -race -cover ./internal/admin/...
go test -v -race -cover ./pkg/safe/...

# Run a specific test function
go test -v -race -run TestFunctionName ./pkg/discovery/

# Run tests with verbose output
go test -v ./...
```

## Architecture

### Services (cmd/ + internal/)

| Service | Entry Point | Description |
|---------|-------------|-------------|
| **admin** | `cmd/admin/` | gRPC + HTTP API server; manages probe configs, service discovery, and database operations |
| **analysis** | `cmd/analysis/` | Failure detection engine; analyzes probe data, triggers switchover workflows |
| **receiver** | `cmd/receiver/` | Data ingestion service; receives probe reports via gRPC (from probes) or Kafka |
| **probe** | `cmd/probe/` | Probing agent; runs MySQL/Redis harvesters and reports to receiver |

### Directory Structure

```
├── cmd/                    # Service entry points (main.go)
│   ├── admin/
│   ├── analysis/
│   ├── receiver/
│   └── probe/
├── internal/               # Service-specific internal code
│   ├── admin/              # Admin service implementation
│   │   ├── apm/           # APM endpoints and metrics
│   │   ├── cmds/          # CLI commands (start, stop, restart, reload, health); migrate lives in command.go
│   │   ├── config/        # Configuration handling
│   │   ├── ginx/          # HTTP error constants, pagination params and JSON response helpers
│   │   ├── migrator/      # Database migration
│   │   ├── slot/          # Resource slots for hot-reload
│   │   ├── strategy/      # Strategy table operations
│   │   ├── switchlog/     # Switchlog table operations
│   │   └── api/open/      # HTTP Open API handlers (gRPC server lives in internal/admin/grpc.go)
│   ├── analysis/          # Analysis service implementation
│   │   ├── apm/           # APM endpoints and metrics
│   │   ├── cmds/          # CLI commands
│   │   ├── config/        # Configuration handling
│   │   ├── detector/      # Failure detectors
│   │   ├── failure/       # Failure event rules (non-switchable filtering)
│   │   ├── parser/        # Status parser registry
│   │   ├── switcher/      # Switchover execution
│   │   ├── workflow/      # Switchover workflow logic
│   │   ├── storage/       # Data storage layer
│   │   ├── testutil/      # Test utilities
│   │   └── dbm/           # DBM API client
│   ├── receiver/          # Receiver service implementation
│   │   ├── apm/           # APM endpoints and metrics
│   │   ├── cmds/          # CLI commands
│   │   ├── config/        # Configuration handling
│   │   ├── source/        # Data sources (probe, kafka)
│   │   └── sink/           # Data sinks (mysql, etc.)
│   └── probe/             # Probe service implementation
│       ├── cmds/           # CLI commands (gen-config, ensure, collect-pause, etc.)
│       ├── config/         # Configuration handling
│       ├── configsync/     # Probe config fetch/render from admin, shared by gen-config and periodic sync
│       ├── harvester/      # Harvester framework (registry.go)
│       │   ├── base/      # Base harvester types
│       │   └── plugin/    # Plugin interface
│       ├── client/         # Admin/receiver clients and Reporter (reporter.go)
│       ├── keepalive/      # Keepalive ping server
│       └── selfmetric/     # Probe self-metrics
│   (DB-specific harvesters live in internal/provider/{mysql,redis}/harvest/)
├── pkg/                    # Shared packages
│   ├── discovery/         # etcd-based service discovery
│   ├── hanet/             # HTTP server/client utilities
│   ├── storage/           # Database storage layers
│   │   ├── hamysql/      # MySQL connection management
│   │   ├── hamodel/      # HA data models (GORM)
│   │   ├── haprobe/      # Probe data storage
│   │   └── haredis/      # Redis connection management
│   ├── dbcred/            # Per-instance probe credential resolution
│   ├── dbtype/            # Cluster type to DbType catalog and capability registry
│   ├── monitor/           # BKMonitor event reporting (via bkmonitorbeat)
│   ├── haapm/             # APM metrics (counter, gauge, histogram, summary)
│   ├── safe/              # Panic-safe goroutine wrappers
│   ├── process/           # Process lifecycle management
│   ├── logger/            # Logging utilities (zap-based)
│   ├── machine/           # Machine ID, snowflake, host info
│   ├── cache/             # Caching utilities
│   ├── probeconfig/       # Probe configuration generation
│   ├── constant/          # Shared constants
│   ├── gerrors/           # Error handling
│   ├── converter/         # Data conversion utilities
│   ├── proto/             # Protocol buffer definitions
│   └── version/           # Version information
├── etc/                    # Configuration templates
├── scripts/                # Deployment and setup scripts
└── tools/                  # Utility binaries (cluster, bwmgr, ha-sandbox-mock, probe-sandbox-mock)
```

## Key Patterns

### Service Command Pattern

Each service uses Cobra for CLI commands. The pattern in `cmd/*/main.go`:
- Root command runs the service (`RunE: service.Run`)
- Common subcommands: `version`, `health`, `start`, `daemon-start`, `stop`, `restart`, `reload`
- admin only: `migrate`; probe only: `gen-config`, `ensure`, `ensure-keepalive`, `collect-pause`, `collect-resume`
- Config file specified via `--config`/`-c` flag (default: `./etc/<service>.yaml`)

### Configuration

- Templates in `etc/templates/*.yaml` with `{{PLACEHOLDER}}` syntax
- Use `scripts/render_configs.py` to generate configs from rc files
- RC examples: `etc/dbha-v2.server.rc.example`, `etc/dbha-v2.probe.rc.example`
- Runtime configs: `etc/admin.yaml`, `etc/analysis.yaml`, `etc/receiver.yaml`, `etc/probe.yaml`
- Toolkit configs: `etc/cluster.yaml`, `etc/bwmgr.yaml` (installed under server deployment root)

### Panic Safety

Use `pkg/safe` wrappers for goroutines to prevent crashes:
```go
safe.Go(func() { /* async work */ })
safe.Run(func() { /* sync work with recover */ })
```

### Service Discovery

Services register via etcd using `pkg/discovery`. The analysis service uses etcd concurrency patterns (mutex, election) for HA coordination.

### Database Access

- `pkg/storage/hamysql` - MySQL connection pooling
- `pkg/storage/hamodel` - GORM models for HA data
- `pkg/storage/haprobe` - Probe data storage

### Testing Patterns

- Test files co-located with source files (`*_test.go`)
- Use `testify` for assertions
- `internal/analysis/testutil/` provides test utilities
- Benchmark functions (`func BenchmarkXxx`) live in regular `*_test.go` files (e.g. `pkg/hanet/gin_server_test.go`)

## Development Scripts

```bash
# Setup development environment
source scripts/devenv.rc

# Render configs for local development
python3 scripts/render_configs.py --module server --rc etc/dbha-v2.server.rc --ip-detect-udp-connect-host <host>
python3 scripts/render_configs.py --module probe --rc etc/dbha-v2.probe.rc --ip-detect-udp-connect-host <host>

# Install build dependencies (requires root)
bash scripts/install-libs.sh

# Deploy services
./scripts/deploy.sh -m install -r server -s <source> -t <target>
./scripts/deploy.sh -m install -r probe -s <source> -t <target>
```
