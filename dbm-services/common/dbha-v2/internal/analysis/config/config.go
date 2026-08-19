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

// Package config provides configuration management for the DBHA v2 analysis module.
package config

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/spf13/viper"
)

// defaultPidFile is the fallback pid-file path used when the loaded config
// leaves pidFile empty, so the running process never operates with an empty
// pid-file path.
const defaultPidFile = "./pids/analysis.pid"

var Cfg = Configuration{
	Name:    "analysis",
	PidFile: defaultPidFile,
	Workflow: WorkflowConfig{
		WorkerBusinessCount:        100,
		LockBusinessWaitTimeout:    5 * time.Second,
		ScanTimeout:                60 * time.Second,
		ScanInterval:               3 * time.Second,
		UpdateDbmCacheInterval:     10 * time.Second,
		ReadDbMetaOffsetDuration:   -24 * time.Hour,
		ReadDbMetricOffsetDuration: -60 * time.Second,
		ReadDbEventOffsetDuration:  -10 * time.Minute,
		PopInterval:                5 * time.Second,
		PopSwitchSemSize:           10,
		WindowDuration:             0,
		InflightTTL:                30 * time.Second,
		SwitchTimeout:              10 * time.Minute,
		DbmApiMetadataHashCnt:      minDbmApiMetadataHashCnt,
		EnableWhiteList:            true,
		SwitchFlow: SwitchFlowConfig{
			HostLevelSwitchMaxHostNum:        32,
			HostLevelSwitchMaxInstanceNum:    64,
			ClusterLevelSwitchMaxClusterNum:  32,
			ClusterLevelSwitchMaxInstanceNum: 64,
			DbmApiMaxConcurrentRequests:      8,
			SwitchLogWriteTimeout:            1 * time.Second,
			DbConnectTimeout:                 3 * time.Second,
			ClusterLockTimeout:               60 * time.Second,
			ExecSqlTimeout:                   6 * time.Second,
			AllowedIgnoreCheckSum:            false,
			AllowedIgnoreSlaveDelay:          false,
			AllowedSlowBytes:                 0,
			AllowedMaxChecksumFailCnt:        2,
			AllowedMaxHeartbeatDelay:         600,
		},
	},

	Monitor: MonitorConfig{
		Timeout: 10 * time.Second,
	},

	Log: LogConfig{
		Path:      "./logs/analysis.log",
		Level:     logger.InfoLevel.String(),
		FileCount: 10,
		FileSize:  100,
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

// DbmApi the API config of the DBM metadata
type DbmApi struct {
	Api     string        `yaml:"api"     mapstructure:"api"`
	Token   string        `yaml:"token"   mapstructure:"token"`
	Timeout time.Duration `yaml:"timeout" mapstructure:"timeout"`
}

// SwitchFlowConfig defines the configuration for the switch flow
type SwitchFlowConfig struct {
	DbmApiMaxConcurrentRequests      int           `yaml:"dbmApiMaxConcurrentRequests"      mapstructure:"dbmApiMaxConcurrentRequests"`
	HostLevelSwitchMaxHostNum        int           `yaml:"hostLevelSwitchMaxHostNum"        mapstructure:"hostLevelSwitchMaxHostNum"`
	HostLevelSwitchMaxInstanceNum    int           `yaml:"hostLevelSwitchMaxInstanceNum"    mapstructure:"hostLevelSwitchMaxInstanceNum"`
	ClusterLevelSwitchMaxClusterNum  int           `yaml:"clusterLevelSwitchMaxClusterNum"  mapstructure:"clusterLevelSwitchMaxClusterNum"`
	ClusterLevelSwitchMaxInstanceNum int           `yaml:"clusterLevelSwitchMaxInstanceNum" mapstructure:"clusterLevelSwitchMaxInstanceNum"`
	SwitchLogWriteTimeout            time.Duration `yaml:"switchLogWriteTimeout"            mapstructure:"switchLogWriteTimeout"`
	DbConnectTimeout                 time.Duration `yaml:"dbConnectTimeout"                 mapstructure:"dbConnectTimeout"`
	ClusterLockTimeout               time.Duration `yaml:"clusterLockTimeout"               mapstructure:"clusterLockTimeout"`
	ExecSqlTimeout                   time.Duration `yaml:"execSqlTimeout"                   mapstructure:"execSqlTimeout"`
	AllowedIgnoreCheckSum            bool          `yaml:"slaveAllowedIgnoreCheckSum"       mapstructure:"slaveAllowedIgnoreCheckSum"`
	AllowedIgnoreSlaveDelay          bool          `yaml:"slaveAllowedIgnoreSlaveDelay"     mapstructure:"slaveAllowedIgnoreSlaveDelay"`
	AllowedSlowBytes                 int           `yaml:"slaveAllowedSlowBytes"            mapstructure:"slaveAllowedSlowBytes"`
	AllowedMaxChecksumFailCnt        int           `yaml:"slaveAllowedMaxChecksumFailCnt"   mapstructure:"slaveAllowedMaxChecksumFailCnt"`
	AllowedMaxHeartbeatDelay         int           `yaml:"slaveAllowedMaxHeartbeatDelay"    mapstructure:"slaveAllowedMaxHeartbeatDelay"`
}

// WorkflowConfig workflow's configuration
type WorkflowConfig struct {
	WorkerBusinessCount        int              `yaml:"workerBusinessCount"        mapstructure:"workerBusinessCount"`
	LockBusinessWaitTimeout    time.Duration    `yaml:"lockBusinessWaitTimeout"    mapstructure:"lockBusinessWaitTimeout"`
	ScanTimeout                time.Duration    `yaml:"scanTimeout"                mapstructure:"scanTimeout"`
	ScanInterval               time.Duration    `yaml:"scanInterval"               mapstructure:"scanInterval"`
	UpdateDbmCacheInterval     time.Duration    `yaml:"updateDbmCacheInterval"     mapstructure:"updateDbmCacheInterval"`
	ReadDbMetaOffsetDuration   time.Duration    `yaml:"readDbMetaOffsetDuration"   mapstructure:"readDbMetaOffsetDuration"`
	ReadDbMetricOffsetDuration time.Duration    `yaml:"readDbMetricOffsetDuration" mapstructure:"readDbMetricOffsetDuration"`
	ReadDbEventOffsetDuration  time.Duration    `yaml:"readDbEventOffsetDuration"  mapstructure:"readDbEventOffsetDuration"`
	EnableSwitching            bool             `yaml:"enableSwitching"            mapstructure:"enableSwitching"`
	EnableWhiteList            bool             `yaml:"enableWhiteList"            mapstructure:"enableWhiteList"`
	WindowDuration             time.Duration    `yaml:"windowDuration"             mapstructure:"windowDuration"`
	PopInterval                time.Duration    `yaml:"popInterval"                mapstructure:"popInterval"`
	PopSwitchSemSize           int              `yaml:"popSwitchSemSize"           mapstructure:"popSwitchSemSize"`
	InflightTTL                time.Duration    `yaml:"inflightTTL"                mapstructure:"inflightTTL"`
	SwitchTimeout              time.Duration    `yaml:"switchTimeout"              mapstructure:"switchTimeout"`
	DbmApiMetadataHashCnt      int              `yaml:"dbmApiMetadataHashCnt"      mapstructure:"dbmApiMetadataHashCnt"`
	SwitchFlow                 SwitchFlowConfig `yaml:"switchflow"                 mapstructure:"switchflow"`
	DbmApiMetadata             DbmApi           `yaml:"dbmApiMetadata"             mapstructure:"dbmApiMetadata"`
	DbmApiUpdateStatus         DbmApi           `yaml:"dbmApiUpdateStatus"         mapstructure:"dbmApiUpdateStatus"`
	DbmApiSwapMysqlRole        DbmApi           `yaml:"dbmApiSwapMysqlRole"        mapstructure:"dbmApiSwapMysqlRole"`
	DbmApiSwapTendisCluster    DbmApi           `yaml:"dbmApiSwapTendisCluster"    mapstructure:"dbmApiSwapTendisCluster"`
	DbmApiDomainGet            DbmApi           `yaml:"dbmApiDomainGet"            mapstructure:"dbmApiDomainGet"`
	DbmApiDomainDelete         DbmApi           `yaml:"dbmApiDomainDelete"         mapstructure:"dbmApiDomainDelete"`
	DbmApiCLBDeregister        DbmApi           `yaml:"dbmApiCLBDeregister"        mapstructure:"dbmApiCLBDeregister"`
	DbmApiPolarisUnbind        DbmApi           `yaml:"dbmApiPolarisUnbind"        mapstructure:"dbmApiPolarisUnbind"`
	DbmApiDumperSwitch         DbmApi           `yaml:"dbmApiDumperSwitch"         mapstructure:"dbmApiDumperSwitch"`
	Dbhav1ApiBlackWhitelistGet DbmApi           `yaml:"dbhav1ApiBlackWhitelistGet" mapstructure:"dbhav1ApiBlackWhitelistGet"`
}

// MysqlDatabaseConfig mysql's configuration
type MysqlDatabaseConfig struct {
	User          string        `yaml:"user"          mapstructure:"user"`
	Password      string        `yaml:"password"      mapstructure:"password"`
	ProxyUser     string        `yaml:"proxyUser"     mapstructure:"proxyUser"`
	ProxyPassword string        `yaml:"proxyPassword" mapstructure:"proxyPassword"`
	Timeout       time.Duration `yaml:"timeout"       mapstructure:"timeout"`
}

// DatabaseConfig database's configuration
type DatabaseConfig struct {
	Mysql MysqlDatabaseConfig `yaml:"mysql" mapstructure:"mysql"`
}

// DetectorConfig detector's configuration
type DetectorConfig struct {
	// CheckProbeProcessCmd remote SSH command; only "cd <workdir> && ./bin/dbha-probe health -j" is allowed.
	CheckProbeProcessCmd string `yaml:"checkProbeProcessCmd" mapstructure:"checkProbeProcessCmd"`
	Ssh                  struct {
		Port     int           `yaml:"port"       mapstructure:"port"`
		User     string        `yaml:"user"       mapstructure:"user"`
		Password string        `yaml:"password"   mapstructure:"password"`
		Timeout  time.Duration `yaml:"timeout"    mapstructure:"timeout"`
	} `yaml:"ssh" mapstructure:"ssh"`
}

// MonitorConfig monitor's configuration
type MonitorConfig struct {
	DataID            uint64        `yaml:"dataID"            mapstructure:"dataID"`
	Timeout           time.Duration `yaml:"timeout"           mapstructure:"timeout"`
	AccessToken       string        `yaml:"accessToken"       mapstructure:"accessToken"`
	BkMonitorBeat     string        `yaml:"bkMonitorBeat"     mapstructure:"bkMonitorBeat"`
	BkMonitorEndpoint string        `yaml:"bkMonitorEndpoint" mapstructure:"bkMonitorEndpoint"`
}

// StorageConfig storage's configuration
type StorageConfig struct {
	Endpoint string        `yaml:"endpoint"  mapstructure:"endpoint"`
	User     string        `yaml:"user"      mapstructure:"user"`
	Password string        `yaml:"password"  mapstructure:"password"`
	Timeout  time.Duration `yaml:"timeout"   mapstructure:"timeout"`
}

// ApmConfig Apm's configuration
type ApmConfig struct {
	ReadTimeout   time.Duration `yaml:"readTimeout"   mapstructure:"readTimeout"`
	WriteTimeout  time.Duration `yaml:"writeTimeout"  mapstructure:"writeTimeout"`
	ListenAddress string        `yaml:"listenAddress" mapstructure:"listenAddress"`
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
	PidFile   string          `yaml:"pidFile"   mapstructure:"pidFile"`
	Discovery DiscoveryConfig `yaml:"discovery" mapstructure:"discovery"`
	Apm       ApmConfig       `yaml:"apm"       mapstructure:"apm"`
	Workflow  WorkflowConfig  `yaml:"workflow"  mapstructure:"workflow"`
	Database  DatabaseConfig  `yaml:"database"  mapstructure:"database"`
	Detector  DetectorConfig  `yaml:"detector"  mapstructure:"detector"`
	Monitor   MonitorConfig   `yaml:"monitor"   mapstructure:"monitor"`
	Storage   StorageConfig   `yaml:"storage"   mapstructure:"storage"`
	Log       LogConfig       `yaml:"log"       mapstructure:"log"`
}

// Load loads analysis configuration from file
func Load(configFilePath string) error {
	viper.SetConfigName("analysis")
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

	Cfg.Workflow.DbmApiMetadataHashCnt = clampDbmApiMetadataHashCnt(Cfg.Workflow.DbmApiMetadataHashCnt)

	if Cfg.PidFile == "" {
		Cfg.PidFile = defaultPidFile
	}

	if Cfg.Detector.CheckProbeProcessCmd == "" {
		Cfg.Detector.CheckProbeProcessCmd = defaultCheckProbeProcessCmd
	}
	if err := validateCheckProbeProcessCmd(Cfg.Detector.CheckProbeProcessCmd); err != nil {
		return err
	}

	return nil
}

// SwitchIDVersion is the version prefix for generated switch IDs
const (
	SwitchIDVersion          = "00"
	minDbmApiMetadataHashCnt = 200
)

func clampDbmApiMetadataHashCnt(hashCnt int) int {
	if hashCnt < minDbmApiMetadataHashCnt {
		logger.Warn(
			"dbm api metadata hash count too small, configured: %d, fallback: %d",
			hashCnt, minDbmApiMetadataHashCnt,
		)
		return minDbmApiMetadataHashCnt
	}

	return hashCnt
}

func init() {
	Cfg.Detector.CheckProbeProcessCmd = defaultCheckProbeProcessCmd
	Cfg.Detector.Ssh.Port = 22
	Cfg.Detector.Ssh.User = "root"
	Cfg.Detector.Ssh.Timeout = 10 * time.Second
	Cfg.Database.Mysql.Timeout = 10 * time.Second
	Cfg.Storage.Timeout = 10 * time.Second
}
