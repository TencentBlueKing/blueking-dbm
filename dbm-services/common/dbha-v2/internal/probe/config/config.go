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

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/viper"
)

// defaultPidFile is the fallback pid-file path used when the loaded config
// leaves pidFile empty, so the running process never operates with an empty
// pid-file path.
const defaultPidFile = "./pids/probe.pid"

// MinSyncInterval is the floor applied to admin.syncInterval.
//
// Each tick costs admin one metadata lookup per probe, so the whole fleet's load scales with
// 1/interval. A typo such as "1s" on a large fleet would be enough to overwhelm admin, and the
// probes causing it are exactly the ones that cannot be reconfigured quickly. Clamping keeps a
// misconfigured probe running at a sane rate instead of refusing to start.
const MinSyncInterval = 10 * time.Second

// Cfg holds the currently applied probe configuration. It is only replaced after
// a successful Parse (via Load or a hot-reload apply path).
//
// Reads on the startup and hot-reload paths are serialized and may use Cfg directly.
// Concurrent readers, in particular background goroutines, must use Snapshot instead.
var Cfg = defaultConfiguration()

// snapshot mirrors Cfg for lock-free concurrent reads. Apply keeps the two in step.
var snapshot atomic.Pointer[Configuration]

func init() {
	initial := Cfg
	snapshot.Store(&initial)
}

// Apply installs next as the applied configuration. It is the single write path: keeping Cfg
// and the snapshot updated together is what lets background readers observe a consistent view.
// Tests that restore a saved configuration must call it too rather than assigning Cfg directly,
// otherwise the snapshot keeps serving the value from the previous test.
func Apply(next Configuration) {
	Cfg = next
	applied := next
	snapshot.Store(&applied)
}

// Snapshot returns the configuration currently applied, without racing against hot reload.
//
// The result is a shallow copy: pointer fields such as Harvester.MySql are shared with the
// applied configuration. That is safe because reload swaps the whole Configuration instead of
// mutating sub-structs in place. Code that starts mutating those sub-structs in place would
// invalidate this guarantee.
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
//
// The block is owned locally: admin has no idea which endpoints this probe was pointed at, so
// a config rewritten from an admin payload has to carry it over from the file on disk. Losing
// it would stop the probe from ever syncing again.
//
// A zero SyncInterval disables periodic sync, which is what every config written before this
// feature existed parses to. Note this differs from admin's own cacheMaxAge, where zero means
// "use the default".
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

// SyncEnabled reports whether periodic sync should run. Endpoints are required: an interval
// with nowhere to send the request would just log a failure on every tick.
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

// MySqlHarvesterConfig MySQL harvester config.
// Timeout bounds both DSN dial timeout (go-sql-driver "timeout=..." DSN parameter) and per-query
// context timeout (gorm WithContext) for every collector built from this block. Admin clamps the
// upstream value at minProbeHarvesterTimeout before sending.
type MySqlHarvesterConfig struct {
	User              string             `yaml:"user"              mapstructure:"user"`
	Password          string             `yaml:"password"          mapstructure:"password"`
	Interval          time.Duration      `yaml:"interval"          mapstructure:"interval"`
	HeartbeatInterval time.Duration      `yaml:"heartbeatInterval" mapstructure:"heartbeatInterval"`
	ReplDelayInterval time.Duration      `yaml:"replDelayInterval" mapstructure:"replDelayInterval"`
	Timeout           time.Duration      `yaml:"timeout"           mapstructure:"timeout"`
	Endpoints         []DbEndpointConfig `yaml:"endpoints"         mapstructure:"endpoints"`
}

// RedisHarvesterConfig Redis harvester config
type RedisHarvesterConfig struct {
	User      string             `yaml:"user"      mapstructure:"user"`
	Password  string             `yaml:"password"  mapstructure:"password"`
	Interval  time.Duration      `yaml:"interval"  mapstructure:"interval"`
	Timeout   time.Duration      `yaml:"timeout"   mapstructure:"timeout"`
	Endpoints []DbEndpointConfig `yaml:"endpoints" mapstructure:"endpoints"`
}

// HarvesterConfig harvester config.
// MySqlProxyAdmin reuses MySqlHarvesterConfig but carries proxy-admin credentials and admin-port-only
// endpoints; probe loads it as a separate MySQL plugin instance so proxy admin ports are probed with
// distinct creds from regular mysql storage/spider endpoints.
type HarvesterConfig struct {
	MySql           *MySqlHarvesterConfig `yaml:"mysql"           mapstructure:"mysql"`
	MySqlProxyAdmin *MySqlHarvesterConfig `yaml:"mysqlProxyAdmin" mapstructure:"mysqlProxyAdmin"`
	Redis           *RedisHarvesterConfig `yaml:"redis"           mapstructure:"redis"`
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
	Name      string          `yaml:"name"      mapstructure:"name"`
	Version   string          `yaml:"version"   mapstructure:"version"`
	ServiceID string          `yaml:"serviceID" mapstructure:"serviceID"`
	PidFile   string          `yaml:"pidFile"   mapstructure:"pidFile"`
	Reporter  *ReporterConfig `yaml:"reporter"  mapstructure:"reporter"`
	Client    ClientConfig    `yaml:"client"    mapstructure:"client"`
	Admin     AdminConfig     `yaml:"admin"     mapstructure:"admin"`
	Harvester HarvesterConfig `yaml:"harvester" mapstructure:"harvester"`
	Log       LogConfig       `yaml:"log"       mapstructure:"log"`
}

// Parse reads probe configuration from path without mutating the package-level Cfg
// or the global viper instance.
//
// When path is empty, Parse looks for a file named "probe" (YAML) under ./etc,
// matching the historical Load behavior. When path is non-empty, that file is used.
// An empty pidFile in the file is normalized to defaultPidFile.
//
// On success it returns a fully populated Configuration starting from
// defaultConfiguration so omitted keys do not retain values from a previous load.
// On failure it returns a zero Configuration and the error; Cfg is untouched.
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

// ParseBytes parses an in-memory YAML document into a Configuration. It shares the defaults
// and post-processing of Parse, so a document accepted here yields exactly the same
// Configuration once it has been written to disk and read back by Parse. Callers rely on that
// equivalence to validate rendered output before overwriting a working config file.
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

// postProcess normalizes a freshly unmarshalled configuration. Parse and ParseBytes must both
// go through it: were the two paths to diverge, a document that validates in memory could parse
// into something different after a round-trip through disk.
func postProcess(cfg *Configuration) {
	if cfg.PidFile == "" {
		cfg.PidFile = defaultPidFile
	}
	clampSyncInterval(cfg)
}

// clampSyncInterval raises a too-small sync interval to MinSyncInterval.
//
// Zero and negative values are left alone: they mean periodic sync is off, which is how every
// config written before this feature existed parses. Only a positive value below the floor is
// a genuine misconfiguration worth correcting.
func clampSyncInterval(cfg *Configuration) {
	if cfg.Admin.SyncInterval <= 0 || cfg.Admin.SyncInterval >= MinSyncInterval {
		return
	}

	logger.Warn("admin sync interval below the allowed floor, configured: %s, applied: %s",
		cfg.Admin.SyncInterval, MinSyncInterval)
	cfg.Admin.SyncInterval = MinSyncInterval
}

// Load loads probe configuration from file into the package-level Cfg.
// It delegates to Parse and only replaces Cfg after a successful parse, so a
// failed load leaves the previously applied configuration intact.
func Load(configFilePath string) error {
	next, err := Parse(configFilePath)
	if err != nil {
		return err
	}
	Apply(next)
	return nil
}

// RetainIdentity copies fields that must not change across a hot reload from old
// into next. PidFile and Log are process-identity settings applied only at
// startup; changing them requires a restart.
// It returns next with those identity fields overwritten from old.
func RetainIdentity(old, next Configuration) Configuration {
	next.PidFile = old.PidFile
	next.Log = old.Log
	return next
}

// defaultConfiguration returns the baseline probe configuration used both as the
// package-level Cfg initial value and as the starting point for Parse, so that
// omitted YAML keys do not retain stale values from a previous load.
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
