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

// Package config provides probe configuration loading, structures, and generation from metadata.
package config

import (
	"bytes"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/viper"
)

// defaultPidFile is the fallback pid-file path used when the loaded config
// leaves pidFile empty, so the running process never operates with an empty
// pid-file path.
const defaultPidFile = "./pids/probe.pid"

// MinSyncInterval is the floor applied to admin.syncInterval.
const MinSyncInterval = 10 * time.Second

// Cfg holds the currently applied probe configuration. Concurrent readers must use Snapshot.
var Cfg = defaultConfiguration()

// snapshot mirrors Cfg for lock-free concurrent reads. Apply keeps the two in step.
var snapshot atomic.Pointer[Configuration]

func init() {
	initial := Cfg
	snapshot.Store(&initial)
}

// Apply installs next as the applied configuration.
func Apply(next Configuration) {
	Cfg = next
	applied := next
	snapshot.Store(&applied)
}

// Snapshot returns the configuration currently applied, without racing against hot reload.
func Snapshot() Configuration {
	if applied := snapshot.Load(); applied != nil {
		return *applied
	}
	return Cfg
}

// ClientConfig holds gRPC client tuning (ping, message sizes) and receiver reconnect settings for the probe agent.
type ClientConfig struct {
	PingTime                     time.Duration `yaml:"pingTime"                     mapstructure:"pingTime"`
	PingTimeout                  time.Duration `yaml:"pingTimeout"                  mapstructure:"pingTimeout"`
	MaxReceiveMessageSize        int           `yaml:"maxReceiveMessageSize"        mapstructure:"maxReceiveMessageSize"`
	MaxSendMessageSize           int           `yaml:"maxSendMessageSize"           mapstructure:"maxSendMessageSize"`
	ReceiverReconnectInterval    time.Duration `yaml:"receiverReconnectInterval"    mapstructure:"receiverReconnectInterval"`
	ReceiverMaxReconnectAttempts int           `yaml:"receiverMaxReconnectAttempts" mapstructure:"receiverMaxReconnectAttempts"`
}

// AdminConfig tells the probe where to refresh its own configuration from, and how often.
type AdminConfig struct {
	Endpoints    []string      `yaml:"endpoints"    mapstructure:"endpoints"`
	BkCloudID    uint64        `yaml:"bkCloudID"    mapstructure:"bkCloudID"`
	LocalIP      string        `yaml:"localIP"      mapstructure:"localIP"`
	SyncInterval time.Duration `yaml:"syncInterval" mapstructure:"syncInterval"`
}

// IsZero reports whether the block carries nothing worth writing to disk.
func (a AdminConfig) IsZero() bool {
	return len(a.Endpoints) == 0 && a.BkCloudID == 0 && a.LocalIP == "" && a.SyncInterval == 0
}

// SyncEnabled reports whether periodic sync should run.
func (a AdminConfig) SyncEnabled() bool {
	return a.SyncInterval > 0 && len(a.Endpoints) > 0
}

// ReporterConfig reporter config
type ReporterConfig struct {
	Name        string        `yaml:"name"        mapstructure:"name"`
	Endpoint    string        `yaml:"endpoint"    mapstructure:"endpoint"`
	DataID      uint64        `yaml:"dataID"      mapstructure:"dataID"`
	ConnTimeout time.Duration `yaml:"connTimeout" mapstructure:"connTimeout"`
	BkCloudID   int           `yaml:"bkCloudID"   mapstructure:"bkCloudID"`
	// LocalSocketPort is the local TCP port used by the GSE agent-report SDK on
	// Windows (the SDK selects domain socket vs local TCP by build tag). Zero
	// means unset: on Unix it is ignored, on Windows it must be provided to report
	// via GSE. Kept optional so existing Linux configs (which omit it) are
	// unaffected and generate byte-identical YAML.
	LocalSocketPort uint `yaml:"localSocketPort" mapstructure:"localSocketPort"`
}

// DbEndpointConfig db instance endpoint config
type DbEndpointConfig struct {
	Proto        string                             `yaml:"proto"        mapstructure:"proto"`
	ClusterType  haprobe.DbmMetadataClusterType     `yaml:"clusterType"  mapstructure:"clusterType"`
	MachineType  haprobe.DbmMetadataMachineType     `yaml:"machineType"  mapstructure:"machineType"`
	InstanceRole haprobe.DbmMetadataInstanceRole    `yaml:"instanceRole" mapstructure:"instanceRole"`
	AccessLayer  haprobe.DbmMetadataAccessLayerType `yaml:"accessLayer"  mapstructure:"accessLayer"`
	Ip           string                             `yaml:"ip"           mapstructure:"ip"`
	Ports        []string                           `yaml:"ports"        mapstructure:"ports"`
	AdminPorts   []string                           `yaml:"adminPorts"   mapstructure:"adminPorts"`
}

// RawHarvesterConfig is the common shape of a probe harvester YAML block.
// Known blocks (mysql / mysqlProxyAdmin / redis) and future DB types share this layout.
// Timeout bounds both DSN dial timeout and per-query context timeout for MySQL collectors.
// HeartbeatInterval / ReplDelayInterval only apply to the MySQL family blocks; other
// DB types leave them zero and their collectors fall back to Interval.
type RawHarvesterConfig struct {
	User              string             `yaml:"user"              mapstructure:"user"`
	Password          string             `yaml:"password"          mapstructure:"password"`
	Interval          time.Duration      `yaml:"interval"          mapstructure:"interval"`
	HeartbeatInterval time.Duration      `yaml:"heartbeatInterval" mapstructure:"heartbeatInterval"`
	ReplDelayInterval time.Duration      `yaml:"replDelayInterval" mapstructure:"replDelayInterval"`
	Timeout           time.Duration      `yaml:"timeout"           mapstructure:"timeout"`
	Endpoints         []DbEndpointConfig `yaml:"endpoints"         mapstructure:"endpoints"`
}

// Well-known harvester block names (YAML keys under harvester:).
const (
	HarvesterBlockMySQL           = "mysql"
	HarvesterBlockMySQLProxyAdmin = "mysqlProxyAdmin"
	HarvesterBlockRedis           = "redis"
)

// Precomputed normalized forms of the well-known block names for Block() lookups.
var (
	normBlockMySQL           = dbtype.NormalizeBlockName(HarvesterBlockMySQL)
	normBlockMySQLProxyAdmin = dbtype.NormalizeBlockName(HarvesterBlockMySQLProxyAdmin)
	normBlockRedis           = dbtype.NormalizeBlockName(HarvesterBlockRedis)
)

// HarvesterConfig keeps named mysql/redis/proxyAdmin fields for viper/mapstructure
// zero regression (viper lowercases bare map keys), and Extra collects new DB blocks
// via mapstructure ",remain".
type HarvesterConfig struct {
	MySql           *RawHarvesterConfig            `yaml:"mysql"           mapstructure:"mysql"`
	MySqlProxyAdmin *RawHarvesterConfig            `yaml:"mysqlProxyAdmin" mapstructure:"mysqlProxyAdmin"`
	Redis           *RawHarvesterConfig            `yaml:"redis"           mapstructure:"redis"`
	Extra           map[string]*RawHarvesterConfig `yaml:",inline"        mapstructure:",remain"`
}

// Block returns the config for a harvester block name, or nil if absent.
// The name is normalized so camelCase and lowercase lookups are equivalent.
func (h HarvesterConfig) Block(name string) *RawHarvesterConfig {
	n := dbtype.NormalizeBlockName(name)
	switch n {
	case normBlockMySQL:
		return h.MySql
	case normBlockMySQLProxyAdmin:
		return h.MySqlProxyAdmin
	case normBlockRedis:
		return h.Redis
	default:
		if h.Extra == nil {
			return nil
		}
		return h.Extra[n]
	}
}

// HasEndpoints reports whether the named block exists and lists at least one endpoint.
func (h HarvesterConfig) HasEndpoints(name string) bool {
	b := h.Block(name)
	return b != nil && len(b.Endpoints) > 0
}

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"      mapstructure:"path"`
	Level     string `yaml:"level"     mapstructure:"level"`
	FileCount int    `yaml:"fileCount" mapstructure:"fileCount"`
	FileSize  int    `yaml:"fileSize"  mapstructure:"fileSize"`
}

// Configuration receiver's configuration
type Configuration struct {
	Name       string          `yaml:"name"       mapstructure:"name"`
	Version    string          `yaml:"version"    mapstructure:"version"`
	ServiceID  string          `yaml:"serviceID"  mapstructure:"serviceID"`
	PidFile    string          `yaml:"pidFile"    mapstructure:"pidFile"`
	Reporter   *ReporterConfig `yaml:"reporter"   mapstructure:"reporter"`
	Client     ClientConfig    `yaml:"client"     mapstructure:"client"`
	Admin      AdminConfig     `yaml:"admin"      mapstructure:"admin"`
	Harvester  HarvesterConfig `yaml:"harvester"  mapstructure:"harvester"`
	Log        LogConfig       `yaml:"log"        mapstructure:"log"`
	ClearPorts []int           `yaml:"clearPorts" mapstructure:"clearPorts"`
}

// Parse reads probe configuration from path without mutating the package-level Cfg
// or the global viper instance.
func Parse(configFilePath string) (Configuration, error) {
	v := newConfigViper()

	if configFilePath != "" {
		v.SetConfigFile(configFilePath)
	}

	if err := v.ReadInConfig(); err != nil {
		return Configuration{}, err
	}

	return unmarshalConfig(v)
}

// ParseBytes parses an in-memory YAML document into a Configuration.
func ParseBytes(data []byte) (Configuration, error) {
	v := newConfigViper()

	if err := v.ReadConfig(bytes.NewReader(data)); err != nil {
		return Configuration{}, err
	}

	return unmarshalConfig(v)
}

func newConfigViper() *viper.Viper {
	v := viper.New()
	v.SetConfigName("probe")
	v.SetConfigType("yaml")
	v.AddConfigPath("./etc")
	return v
}

func unmarshalConfig(v *viper.Viper) (Configuration, error) {
	next := defaultConfiguration()
	if err := v.Unmarshal(&next); err != nil {
		return Configuration{}, err
	}

	postProcess(&next)
	return next, nil
}

func postProcess(cfg *Configuration) {
	if cfg.PidFile == "" {
		cfg.PidFile = defaultPidFile
	}
	clampSyncInterval(cfg)
	normalizeHarvesterExtraKeysOn(cfg)
}

func clampSyncInterval(cfg *Configuration) {
	if cfg.Admin.SyncInterval <= 0 || cfg.Admin.SyncInterval >= MinSyncInterval {
		return
	}

	logger.Warn("admin sync interval below the allowed floor, configured: %s, applied: %s",
		cfg.Admin.SyncInterval, MinSyncInterval)
	cfg.Admin.SyncInterval = MinSyncInterval
}

// Load loads probe configuration from file into the package-level Cfg.
func Load(configFilePath string) error {
	next, err := Parse(configFilePath)
	if err != nil {
		return err
	}
	Apply(next)
	return nil
}

// RetainIdentity copies fields that must not change across a hot reload from old into next.
func RetainIdentity(old, next Configuration) Configuration {
	next.PidFile = old.PidFile
	next.Log = old.Log
	return next
}

func defaultConfiguration() Configuration {
	return Configuration{
		Name:    "probe",
		PidFile: defaultPidFile,
		Log: LogConfig{
			Path:      "./logs/probe.log",
			Level:     logger.InfoLevel.String(),
			FileCount: 10,
			FileSize:  100,
		},
	}
}

// normalizeHarvesterExtraKeys rebuilds Extra so every map key is normalized.
func normalizeHarvesterExtraKeys() {
	normalizeHarvesterExtraKeysOn(&Cfg)
}

func normalizeHarvesterExtraKeysOn(cfg *Configuration) {
	extra := cfg.Harvester.Extra
	if len(extra) == 0 {
		return
	}
	normalized := make(map[string]*RawHarvesterConfig, len(extra))
	for k, v := range extra {
		normalized[dbtype.NormalizeBlockName(k)] = v
	}
	cfg.Harvester.Extra = normalized
}
