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

package config

var Cfg Configuration

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"      mapstructure:"path"`
	Level     string `yaml:"level"     mapstructure:"level"`
	FileCount int    `yaml:"fileCount" mapstructure:"fileCount"`
	FileSize  int    `yaml:"fileSize"  mapstructure:"fileSize"`
}

// AdminService admin service configuration
type AdminService struct {
	Endpoints    string `yaml:"endpoints"    mapstructure:"endpoints"`
	SyncInterval int    `yaml:"syncInterval" mapstructure:"syncInterval"`
}

// ReceiverService receiver service configuration
type ReceiverService struct {
	Endpoints    string `yaml:"endpoints"     mapstructure:"endpoints"`
	SyncInterval int    `yaml:"syncInterval"  mapstructure:"syncInterval"`
}

// InstanceConfig single instance config
type InstanceConfig struct {
	Host     string `yaml:"host"     mapstructure:"host"`
	Port     int    `yaml:"port"     mapstructure:"port"`
	User     string `yaml:"user"     mapstructure:"user"`
	Password string `yaml:"password" mapstructure:"password"`
	Name     string `yaml:"name"     mapstructure:"name"`
}

// HarvesterConfig harvester's config
type HarvesterConfig struct {
	Name           string           `yaml:"name"            mapstructure:"name"`
	ReportInterval int              `yaml:"reportInterval"  mapstructure:"reportInterval"`
	Instances      []InstanceConfig `yaml:"instances"       mapstructure:"instances"`
}

// Configuration receiver's configuration
type Configuration struct {
	Name      string            `yaml:"name"        mapstructure:"name"`
	Version   string            `yaml:"version"     mapstructure:"version"`
	Admin     AdminService      `yaml:"admin"       mapstructure:"admin"`
	Receiver  ReceiverService   `yaml:"receiver"    mapstructure:"receiver"`
	Harvester []HarvesterConfig `yaml:"harvester"   mapstructure:"harvester"`
	Log       LogConfig         `yaml:"log"         mapstructure:"log"`
	GSE       GSEConfig         `yaml:"gse"         mapstructure:"gse"`
}

// GSEConfig defines the GSE basic config.
type GSEConfig struct {
	// DomainSocketPath is the domain socket path.
	// DataID is the data-id(channel-id) to report.
	DomainSocketPath string `yaml:"domain_socket_path" mapstructure:"domain_socket_path"`
	DataID           uint32 `yaml:"data_id"            mapstructure:"data_id"`
}
