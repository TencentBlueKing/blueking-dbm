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

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// InstanceAddress represents the address of a database instance.
type InstanceAddress struct {
	Host string `yaml:"host"`
	Port int    `yaml:"port"`
}

// ProxyAddress represents the address of a mysql proxy server.
type ProxyAddress struct {
	Host      string `yaml:"host"`
	Port      int    `yaml:"port"`
	AdminPort int    `yaml:"adminPort"`
}

// MysqlCluster represents a MySQL cluster.
type MysqlCluster struct {
	Domain  string            `yaml:"domain"`
	BkBizId int               `yaml:"bkBizId"`
	Proxy   []ProxyAddress    `yaml:"proxy"`
	Master  InstanceAddress   `yaml:"master"`
	Slave   []InstanceAddress `yaml:"slave"`
}

// TenDBInfo represents the information of a TenDB instance.
type TenDBInfo struct {
	Host       string `yaml:"host"`
	Port       int    `yaml:"port"`
	ServerName string `yaml:"serverName"`
	Username   string `yaml:"username"`
	Password   string `yaml:"password"`
	Wrapper    string `yaml:"wrapper"`
}

// RemoteSlaveInfo represents the information of a remote slave instance.
type RemoteSlaveInfo struct {
	TenDBInfo  `yaml:",inline"`
	MasterHost string `yaml:"masterHost"` // Identify the master-slave one-to-one relationship
	MasterPort int    `yaml:"masterPort"` // Identify the master-slave one-to-one relationship
}

// TenDBCluster represents a TenDB cluster.
type TenDBCluster struct {
	Domain       string            `yaml:"domain"`
	BkBizId      int               `yaml:"bkBizId"`
	Spider       []TenDBInfo       `yaml:"spider"`
	SpiderSlave  []TenDBInfo       `yaml:"spiderSlave"`
	CtlMaster    TenDBInfo         `yaml:"ctlMaster"`
	CtlSlave     []TenDBInfo       `yaml:"ctlSlave"`
	RemoteMaster []TenDBInfo       `yaml:"remoteMaster"`
	RemoteSlave  []RemoteSlaveInfo `yaml:"remoteSlave"`
}

// BinlogInfo represents mysql binlog information.
type BinlogInfo struct {
	TenDBInfo
	File     string `yaml:"file"`
	Position uint64 `yaml:"position"`
}

// APIConfig represents API configuration
type APIConfig struct {
	Api     string        `yaml:"api"`
	Timeout time.Duration `yaml:"timeout"`
	Token   string        `yaml:"token"`
}

// DbmApis represents DBM apis configurations
type DbmApis struct {
	DbmApiMetadata      APIConfig `yaml:"dbmApiMetadata"`
	DbmApiUpdateStatus  APIConfig `yaml:"dbmApiUpdateStatus"`
	DbmApiSwapMysqlRole APIConfig `yaml:"dbmApiSwapMysqlRole"`
	DbmApiDomainGet     APIConfig `yaml:"dbmApiDomainGet"`
	DbmApiDomainPut     APIConfig `yaml:"dbmApiDomainPut"`
}

// AuthInfo represents authentication information for MySQL instances
type AuthInfo struct {
	User          string `yaml:"user"`
	Password      string `yaml:"password"`
	ProxyUser     string `yaml:"proxyUser"`
	ProxyPassword string `yaml:"proxyPassword"`
	ReplUser      string `yaml:"replUser"`
	ReplPassword  string `yaml:"replPassword"`
}

// Config represents the configuration of the test tools.
type Config struct {
	MysqlClusters []MysqlCluster `yaml:"mysqlClusters"`
	TenDBClusters []TenDBCluster `yaml:"tenDBClusters"`
	DbmServices   DbmApis        `yaml:"dbmServices"`
	AuthInfo      AuthInfo       `yaml:"authInfo"`
}

// ClusterConfig represents the global cluster configuration instance
var ClusterConfig *Config

// SetClusterConfig sets the global configuration
func SetClusterConfig(config *Config) {
	ClusterConfig = config
}

// LoadConfig loads configuration from YAML file
func LoadConfig(configFile string) (*Config, error) {
	data, err := os.ReadFile(configFile)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %v", err)
	}

	var config Config
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, fmt.Errorf("failed to parse config: %v", err)
	}

	return &config, nil
}
