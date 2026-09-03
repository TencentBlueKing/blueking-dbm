/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Package config provides configuration management for the DBHA v2 admin module.
package config

import (
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/spf13/viper"
)

// minProbeGseConnTimeout is the lower bound enforced by clampProbeGseConnTimeout
// when probeGse.connTimeout is empty, invalid, or below this duration.
const minProbeGseConnTimeout = 5 * time.Second

// minProbeHarvesterInterval / minProbeHarvesterTimeout are lower bounds enforced at admin load
// for ProbeMysql / ProbeRedis / ProbeProxyAdmin Interval / Timeout fields. Values that are
// zero or below the minimum are normalized so probe never receives 0s and starts a
// zero-interval ticker.
// minProbeHarvesterHeartbeatInterval / minProbeHarvesterReplHeartbeatInterval are the floors
// for heartbeatInterval / replDelayInterval on probeMysql and probeProxyAdmin.
// Empty YAML values are not clamped here: viper's duration decoder rejects them and Load returns
// an error before clamp runs, so callers must always supply a parseable Go duration string.
const (
	minProbeHarvesterInterval              = 5 * time.Second
	minProbeHarvesterHeartbeatInterval     = 1 * time.Second
	minProbeHarvesterReplHeartbeatInterval = 5 * time.Second
	minProbeHarvesterTimeout               = 1 * time.Second
)

// defaultPidFile is the fallback pid-file path used when the loaded config
// leaves pidFile empty, so the running process never operates with an empty
// pid-file path.
const defaultPidFile = "./pids/admin.pid"

const (
	// DefaultProbeMetadataCacheMaxAge is how fresh cached metadata must be to answer a probe.
	// Ten minutes is comfortably longer than a metadata sync cycle, so the cache still absorbs
	// nearly all requests, while a genuinely lagging sync is caught before probes act on it.
	DefaultProbeMetadataCacheMaxAge = 10 * time.Minute

	// DefaultProbeMetadataTombstoneAge is when a cached row stops counting at all. A day is far
	// beyond any sync delay, so anything older describes an instance metadata sync no longer
	// refreshes rather than one it is late on.
	DefaultProbeMetadataTombstoneAge = 24 * time.Hour

	// minProbeMetadataCacheMaxAge keeps the freshness window above a single sync cycle. Below
	// it, ordinary sync jitter would look like staleness and send every request to DBM.
	minProbeMetadataCacheMaxAge = 1 * time.Minute
)

var Cfg = Configuration{
	Name:    "admin",
	PidFile: defaultPidFile,
	Log: LogConfig{
		Path:      "./logs/admin.log",
		Level:     logger.InfoLevel.String(),
		FileCount: 10,
		FileSize:  100,
	},

	Grpc: GrpcConfig{
		ServerPingTime:        constant.DefaultServerPingTime,
		PingTimeout:           constant.DefaultPingTimeout,
		KeepAliveMinTime:      constant.DefaultKeepAliveMiniTime,
		PermitWithoutStream:   true,
		MaxReceiveMessageSize: constant.DefaultMaxReceiveMessageSize,
		MaxSendMessageSize:    constant.DefaultMaxSendMessageSize,
	},
}

// DiscoveryConfig discovery configuration
type DiscoveryConfig struct {
	Endpoint             string        `yaml:"endpoint"              mapstructure:"endpoint"`
	User                 string        `yaml:"user"                  mapstructure:"user"`
	Password             string        `yaml:"password"              mapstructure:"password"`
	CertFile             string        `yaml:"certFile"              mapstructure:"certFile"`
	KeyFile              string        `yaml:"keyFile"               mapstructure:"keyFile"`
	TrustedCAFile        string        `yaml:"trustedCAFile"         mapstructure:"trustedCAFile"`
	ServiceTimerInterval time.Duration `yaml:"serviceTimerInterval"  mapstructure:"serviceTimerInterval"`
	ServiceUpdateTimeout time.Duration `yaml:"serviceUpdateTimeout"  mapstructure:"serviceUpdateTimeout"`
}

// ApmConfig apm's configuration
type ApmConfig struct {
	ReadTimeout   time.Duration `yaml:"readTimeout"   mapstructure:"readTimeout"`
	WriteTimeout  time.Duration `yaml:"writeTimeout"  mapstructure:"writeTimeout"`
	ListenAddress string        `yaml:"listenAddress" mapstructure:"listenAddress"`
}

// GrpcConfig grpc configuration
type GrpcConfig struct {
	ListenAddress         string        `yaml:"listenAddress"         mapstructure:"listenAddress"`
	ServerPingTime        time.Duration `yaml:"serverPingTime"        mapstructure:"serverPingTime"`
	PingTimeout           time.Duration `yaml:"pingTimeout"           mapstructure:"pingTimeout"`
	KeepAliveMinTime      time.Duration `yaml:"keepAliveMinTime"      mapstructure:"keepAliveMinTime"`
	PermitWithoutStream   bool          `yaml:"permitWithoutStream"   mapstructure:"permitWithoutStream"`
	MaxReceiveMessageSize int           `yaml:"maxReceiveMessageSize" mapstructure:"maxReceiveMessageSize"`
	MaxSendMessageSize    int           `yaml:"maxSendMessageSize"    mapstructure:"maxSendMessageSize"`
}

// WebConfig web configuration. ListenAddress accepts host:port or http://host:port;
// an omitted scheme defaults to http at the call site.
type WebConfig struct {
	ListenAddress string        `yaml:"listenAddress" mapstructure:"listenAddress"`
	ReadTimeout   time.Duration `yaml:"readTimeout"   mapstructure:"readTimeout"`
	WriteTimeout  time.Duration `yaml:"writeTimeout"  mapstructure:"writeTimeout"`
}

// DbmApi the API config of the DBM metadata
type DbmApi struct {
	Name    string        `yaml:"name"    mapstructure:"name"`
	Api     string        `yaml:"api"     mapstructure:"api"`
	Token   string        `yaml:"token"   mapstructure:"token"`
	Method  string        `yaml:"method"  mapstructure:"method"`
	Timeout time.Duration `yaml:"timeout" mapstructure:"timeout"`
}

// StorageConfig dbha database configuration
type StorageConfig struct {
	Endpoint string `yaml:"endpoint" mapstructure:"endpoint"`
	User     string `yaml:"user"     mapstructure:"user"`
	Password string `yaml:"password" mapstructure:"password"`
}

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"      mapstructure:"path"`
	Level     string `yaml:"level"     mapstructure:"level"`
	FileCount int    `yaml:"fileCount" mapstructure:"fileCount"`
	FileSize  int    `yaml:"fileSize"  mapstructure:"fileSize"`
}

// ProbeMetadataConfig bounds how admin's local metadata cache may be used when answering a
// probe's config request.
//
// Both fields treat zero as "use the default", which is the opposite of the probe's
// admin.syncInterval where zero disables the feature. The difference is deliberate: an existing
// admin config has no probeMetadata block, and defaulting it to "no freshness check" would keep
// serving the stale data this exists to avoid.
type ProbeMetadataConfig struct {
	// CacheMaxAge is how recently a cached row must have been refreshed to be trusted. When any
	// row for an IP is older, the whole machine is re-read from DBM.
	CacheMaxAge time.Duration `yaml:"cacheMaxAge"  mapstructure:"cacheMaxAge"`
	// TombstoneAge is the age past which a cached row is ignored outright. Metadata sync has no
	// delete path, so rows for decommissioned instances stay behind forever; without this, one
	// such row would push every request for that IP to DBM for good.
	TombstoneAge time.Duration `yaml:"tombstoneAge" mapstructure:"tombstoneAge"`
}

// ProbeGseConfig defaults for probe GSE reporter; admin loads from YAML and passes to probe.
type ProbeGseConfig struct {
	Endpoint    string `yaml:"endpoint"    mapstructure:"endpoint"`
	DataID      uint64 `yaml:"dataID"      mapstructure:"dataID"`
	ConnTimeout string `yaml:"connTimeout" mapstructure:"connTimeout"`
	// LocalSocketPort is the local TCP port Windows probes use for the GSE
	// agent-report SDK. Optional: unset (zero) means Linux probes ignore it and
	// the probe falls back to the domain socket, preserving existing behavior.
	LocalSocketPort uint `yaml:"localSocketPort" mapstructure:"localSocketPort"`
}

// ProbeMysqlConfig defaults for probe MySQL harvester; admin loads from YAML and always returns
// these defaults to every probe via GetProbeConfig. Probe routes harvester per endpoint based on
// (access_layer, machine_type); these credentials are applied to all mysql-family endpoints
// except TendbHA mysql-proxy (access_layer=proxy AND machine_type=proxy); includes spider admin/ctl.
type ProbeMysqlConfig struct {
	User              string        `yaml:"user"              mapstructure:"user"`
	Password          string        `yaml:"password"          mapstructure:"password"`
	Interval          time.Duration `yaml:"interval"          mapstructure:"interval"`
	HeartbeatInterval time.Duration `yaml:"heartbeatInterval" mapstructure:"heartbeatInterval"`
	ReplDelayInterval time.Duration `yaml:"replDelayInterval" mapstructure:"replDelayInterval"`
	Timeout           time.Duration `yaml:"timeout"           mapstructure:"timeout"`
}

// ProbeRedisConfig defaults for probe Redis harvester; admin loads from YAML and always returns
// these defaults to every probe via GetProbeConfig. Probe routes harvester per endpoint based on
// (access_layer, machine_type); these credentials are applied to all redis-family endpoints
// (includes twemproxy/predixy admin ports).
type ProbeRedisConfig struct {
	User     string        `yaml:"user"     mapstructure:"user"`
	Password string        `yaml:"password" mapstructure:"password"`
	Interval time.Duration `yaml:"interval" mapstructure:"interval"`
	Timeout  time.Duration `yaml:"timeout"  mapstructure:"timeout"`
}

// ProbeProxyAdminConfig defaults for probe proxy-admin harvester; admin loads from YAML and
// always returns these defaults to every probe via GetProbeConfig. Probe routes harvester per
// endpoint based on (access_layer, machine_type); these credentials are applied only to TendbHA
// mysql-proxy endpoints (access_layer=proxy AND machine_type=proxy) and only their AdminPorts.
type ProbeProxyAdminConfig struct {
	User              string        `yaml:"user"              mapstructure:"user"`
	Password          string        `yaml:"password"          mapstructure:"password"`
	Interval          time.Duration `yaml:"interval"          mapstructure:"interval"`
	HeartbeatInterval time.Duration `yaml:"heartbeatInterval" mapstructure:"heartbeatInterval"`
	ReplDelayInterval time.Duration `yaml:"replDelayInterval" mapstructure:"replDelayInterval"`
	Timeout           time.Duration `yaml:"timeout"           mapstructure:"timeout"`
}

// ProbeHarvesterCred is a generic harvester credential block for newly added DB types.
// Keys under ProbeHarvesters map to ProbeConfigPayload.Harvesters (pass-through).
type ProbeHarvesterCred struct {
	User     string        `yaml:"user"     mapstructure:"user"`
	Password string        `yaml:"password" mapstructure:"password"`
	Interval time.Duration `yaml:"interval" mapstructure:"interval"`
	Timeout  time.Duration `yaml:"timeout"  mapstructure:"timeout"`
}

// Configuration admin's configuration
type Configuration struct {
	Name            string                        `yaml:"name"            mapstructure:"name"`
	Version         string                        `yaml:"version"         mapstructure:"version"`
	PidFile         string                        `yaml:"pidFile"         mapstructure:"pidFile"`
	DocFileDir      string                        `yaml:"docFileDir"      mapstructure:"docFileDir"`
	Discovery       DiscoveryConfig               `yaml:"discovery"       mapstructure:"discovery"`
	Apm             ApmConfig                     `yaml:"apm"             mapstructure:"apm"`
	Grpc            GrpcConfig                    `yaml:"grpc"            mapstructure:"grpc"`
	Web             WebConfig                     `yaml:"web"             mapstructure:"web"`
	DbmApis         []DbmApi                      `yaml:"dbmApi"          mapstructure:"dbmApi"`
	Storage         StorageConfig                 `yaml:"storage"         mapstructure:"storage"`
	Log             LogConfig                     `yaml:"log"             mapstructure:"log"`
	ProbeGse        ProbeGseConfig                `yaml:"probeGse"        mapstructure:"probeGse"`
	ProbeMysql      ProbeMysqlConfig              `yaml:"probeMysql"      mapstructure:"probeMysql"`
	ProbeRedis      ProbeRedisConfig              `yaml:"probeRedis"      mapstructure:"probeRedis"`
	ProbeProxyAdmin ProbeProxyAdminConfig         `yaml:"probeProxyAdmin" mapstructure:"probeProxyAdmin"`
	ProbeHarvesters map[string]ProbeHarvesterCred `yaml:"probeHarvesters" mapstructure:"probeHarvesters"`
	ProbeMetadata   ProbeMetadataConfig           `yaml:"probeMetadata"   mapstructure:"probeMetadata"`
}

// clampProbeGseConnTimeout returns at least minProbeGseConnTimeout: empty,
// unparseable, or values strictly below the minimum are rounded up.
func clampProbeGseConnTimeout(raw string) string {
	s := strings.TrimSpace(raw)
	if s == "" {
		return minProbeGseConnTimeout.String()
	}

	d, err := time.ParseDuration(s)
	if err != nil {
		logger.Warn("probeGse connTimeout invalid, using minimum, errmsg: %s", err)
		return minProbeGseConnTimeout.String()
	}

	if d < minProbeGseConnTimeout {
		return minProbeGseConnTimeout.String()
	}

	return s
}

// clampProbeHarvesterInterval returns at least floor; values that are zero or below floor
// are normalized to floor. name is the harvester field label (e.g. "probeMysql.interval")
// used only for the warn log.
func clampProbeHarvesterInterval(name string, d, floor time.Duration) time.Duration {
	if d < floor {
		logger.Warn(
			"probe harvester interval below minimum, normalizing, name: %s, given: %s, minimum: %s",
			name, d, floor,
		)
		return floor
	}
	return d
}

// clampProbeHarvesterTimeout returns at least minProbeHarvesterTimeout; values that are zero
// or below the minimum are normalized to the minimum. name is the harvester block label
// (e.g. "probeRedis") used only for the warn log.
func clampProbeHarvesterTimeout(name string, d time.Duration) time.Duration {
	if d < minProbeHarvesterTimeout {
		logger.Warn(
			"probe harvester timeout below minimum, normalizing, name: %s, given: %s, minimum: %s",
			name, d, minProbeHarvesterTimeout,
		)
		return minProbeHarvesterTimeout
	}
	return d
}

// Load loads admin configuration from file
func Load(configFilePath string) error {
	viper.SetConfigName("admin")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")

	if configFilePath != "" {
		viper.SetConfigFile(configFilePath)
	}

	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	if err := viper.Unmarshal(&Cfg); err != nil {
		return err
	}

	if Cfg.PidFile == "" {
		Cfg.PidFile = defaultPidFile
	}

	Cfg.ProbeGse.ConnTimeout = clampProbeGseConnTimeout(Cfg.ProbeGse.ConnTimeout)

	clampProbeHarvesterDurations()

	Cfg.ProbeMetadata = normalizeProbeMetadata(Cfg.ProbeMetadata)

	return nil
}

// normalizeProbeMetadata fills in the defaults and enforces the freshness floor. Unlike the
// harvester clamps, zero here means "not configured" rather than "configured as zero", because
// an admin config predating this block must keep behaving sensibly.
func normalizeProbeMetadata(cfg ProbeMetadataConfig) ProbeMetadataConfig {
	if cfg.CacheMaxAge <= 0 {
		cfg.CacheMaxAge = DefaultProbeMetadataCacheMaxAge
	} else if cfg.CacheMaxAge < minProbeMetadataCacheMaxAge {
		logger.Warn(
			"probe metadata cacheMaxAge below minimum, normalizing, given: %s, minimum: %s",
			cfg.CacheMaxAge, minProbeMetadataCacheMaxAge,
		)
		cfg.CacheMaxAge = minProbeMetadataCacheMaxAge
	}

	if cfg.TombstoneAge <= 0 {
		cfg.TombstoneAge = DefaultProbeMetadataTombstoneAge
	}

	// A tombstone window shorter than the freshness window would discard rows that are still
	// considered fresh, leaving no configuration that can ever be served from cache.
	if cfg.TombstoneAge < cfg.CacheMaxAge {
		logger.Warn(
			"probe metadata tombstoneAge below cacheMaxAge, raising it, tombstoneAge: %s, cacheMaxAge: %s",
			cfg.TombstoneAge, cfg.CacheMaxAge,
		)
		cfg.TombstoneAge = cfg.CacheMaxAge
	}

	return cfg
}

// clampProbeHarvesterDurations normalizes every probe harvester interval / timeout in Cfg
// against its floor, so probe never receives a zero or too-aggressive cadence.
func clampProbeHarvesterDurations() {
	Cfg.ProbeMysql.Interval = clampProbeHarvesterInterval(
		"probeMysql.interval", Cfg.ProbeMysql.Interval, minProbeHarvesterInterval)
	Cfg.ProbeMysql.HeartbeatInterval = clampProbeHarvesterInterval(
		"probeMysql.heartbeatInterval", Cfg.ProbeMysql.HeartbeatInterval, minProbeHarvesterHeartbeatInterval)
	Cfg.ProbeMysql.ReplDelayInterval = clampProbeHarvesterInterval(
		"probeMysql.replDelayInterval", Cfg.ProbeMysql.ReplDelayInterval, minProbeHarvesterReplHeartbeatInterval)
	Cfg.ProbeMysql.Timeout = clampProbeHarvesterTimeout("probeMysql.timeout", Cfg.ProbeMysql.Timeout)

	Cfg.ProbeRedis.Interval = clampProbeHarvesterInterval(
		"probeRedis.interval", Cfg.ProbeRedis.Interval, minProbeHarvesterInterval)
	Cfg.ProbeRedis.Timeout = clampProbeHarvesterTimeout("probeRedis.timeout", Cfg.ProbeRedis.Timeout)

	Cfg.ProbeProxyAdmin.Interval = clampProbeHarvesterInterval(
		"probeProxyAdmin.interval", Cfg.ProbeProxyAdmin.Interval, minProbeHarvesterInterval)
	Cfg.ProbeProxyAdmin.HeartbeatInterval = clampProbeHarvesterInterval(
		"probeProxyAdmin.heartbeatInterval", Cfg.ProbeProxyAdmin.HeartbeatInterval,
		minProbeHarvesterHeartbeatInterval)
	Cfg.ProbeProxyAdmin.ReplDelayInterval = clampProbeHarvesterInterval(
		"probeProxyAdmin.replDelayInterval", Cfg.ProbeProxyAdmin.ReplDelayInterval,
		minProbeHarvesterReplHeartbeatInterval)
	Cfg.ProbeProxyAdmin.Timeout = clampProbeHarvesterTimeout("probeProxyAdmin.timeout", Cfg.ProbeProxyAdmin.Timeout)

	for name, cred := range Cfg.ProbeHarvesters {
		cred.Interval = clampProbeHarvesterInterval(
			"probeHarvesters."+name+".interval", cred.Interval, minProbeHarvesterInterval)
		cred.Timeout = clampProbeHarvesterTimeout("probeHarvesters."+name+".timeout", cred.Timeout)
		Cfg.ProbeHarvesters[name] = cred
	}
}
