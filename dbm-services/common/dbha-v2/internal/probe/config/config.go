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

// Package config provides probe configuration loading and structures.
package config

import (
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/viper"
)

var Cfg = Configuration{
	Name:    "probe",
	PidFile: "./pids/probe.pid",
	Log: LogConfig{
		Path:      "./logs/probe.log",
		Level:     logger.InfoLevel.String(),
		FileCount: 10,
		FileSize:  100,
	},
}

// ReporterConfig reporter config
type ReporterConfig struct {
	Name        string        `yaml:"name"        mapstructure:"name"`
	Endpoint    string        `yaml:"endpoint"    mapstructure:"endpoint"`
	DataID      uint64        `yaml:"dataID"      mapstructure:"dataID"`
	ConnTimeout time.Duration `yaml:"connTimeout" mapstructure:"connTimeout"`
}

// DbEndpointConfig db instance endpoint config
type DbEndpointConfig struct {
	Proto       string                             `yaml:"proto"       mapstructure:"proto"`
	ClusterType haprobe.DbmMetadataClusterType     `yaml:"clusterType" mapstructure:"clusterType"`
	MachineType haprobe.DbmMetadataMachineType     `yaml:"machineType" mapstructure:"machineType"`
	AccessLayer haprobe.DbmMetadataAccessLayerType `yaml:"accessLayer" mapstructure:"accessLayer"`
	Ip          string                             `yaml:"ip"          mapstructure:"ip"`
	Ports       []string                           `yaml:"ports"       mapstructure:"ports"`
	AdminPorts  []string                           `yaml:"adminPorts"  mapstructure:"adminPorts"`
}

// MySqlHarvesterConfig MySQL harvester config
type MySqlHarvesterConfig struct {
	User      string             `yaml:"user"      mapstructure:"user"`
	Password  string             `yaml:"password"  mapstructure:"password"`
	Interval  time.Duration      `yaml:"interval"  mapstructure:"interval"`
	Endpoints []DbEndpointConfig `yaml:"endpoints" mapstructure:"endpoints"`
}

// RedisHarvesterConfig Redis harvester config
type RedisHarvesterConfig struct {
	Password  string             `yaml:"password"  mapstructure:"password"`
	Interval  time.Duration      `yaml:"interval"  mapstructure:"interval"`
	Timeout   time.Duration      `yaml:"timeout"   mapstructure:"timeout"`
	Endpoints []DbEndpointConfig `yaml:"endpoints" mapstructure:"endpoints"`
}

// HarvesterConfig harvester config
type HarvesterConfig struct {
	MySql *MySqlHarvesterConfig
	Redis *RedisHarvesterConfig
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

	return viper.Unmarshal(&Cfg)
}
