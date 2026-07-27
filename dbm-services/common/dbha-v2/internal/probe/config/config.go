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

var Cfg = Configuration{
	Name:    "probe",
	PidFile: defaultPidFile,
	Log: LogConfig{
		Path:      "./logs/probe.log",
		Level:     logger.InfoLevel.String(),
		FileCount: 10,
		FileSize:  100,
	},
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
type RawHarvesterConfig struct {
	User      string             `yaml:"user"      mapstructure:"user"`
	Password  string             `yaml:"password"  mapstructure:"password"`
	Interval  time.Duration      `yaml:"interval"  mapstructure:"interval"`
	Timeout   time.Duration      `yaml:"timeout"   mapstructure:"timeout"`
	Endpoints []DbEndpointConfig `yaml:"endpoints" mapstructure:"endpoints"`
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
	Name      string          `yaml:"name"      mapstructure:"name"`
	Version   string          `yaml:"version"   mapstructure:"version"`
	ServiceID string          `yaml:"serviceID" mapstructure:"serviceID"`
	PidFile   string          `yaml:"pidFile"   mapstructure:"pidFile"`
	Reporter  *ReporterConfig `yaml:"reporter"  mapstructure:"reporter"`
	Client    ClientConfig    `yaml:"client"    mapstructure:"client"`
	Harvester HarvesterConfig `yaml:"harvester" mapstructure:"harvester"`
	Log       LogConfig       `yaml:"log"       mapstructure:"log"`
}

// Load loads probe configuration from file
func Load(configFilePath string) error {
	viper.SetConfigName("probe")
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

	normalizeHarvesterExtraKeys()

	if Cfg.PidFile == "" {
		Cfg.PidFile = defaultPidFile
	}

	return nil
}

// normalizeHarvesterExtraKeys rebuilds Extra so every map key is normalized.
// viper already lowercases bare map keys; this keeps the invariant explicit for
// any future loader that might preserve camelCase.
func normalizeHarvesterExtraKeys() {
	extra := Cfg.Harvester.Extra
	if len(extra) == 0 {
		return
	}
	normalized := make(map[string]*RawHarvesterConfig, len(extra))
	for k, v := range extra {
		normalized[dbtype.NormalizeBlockName(k)] = v
	}
	Cfg.Harvester.Extra = normalized
}
