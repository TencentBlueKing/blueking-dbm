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
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
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

// ClbConfig represents a Clb binding for cluster instances.
type ClbConfig struct {
	BkCloudID      int               `yaml:"bkCloudId"`
	Region         string            `yaml:"region"`
	ListenerID     string            `yaml:"listenerId"`
	LoadBalancerID string            `yaml:"loadbalancerId"`
	Instances      []InstanceAddress `yaml:"instances"`
}

// BinlogInfo represents mysql binlog information.
type BinlogInfo struct {
	TenDBClusterNodeInfo
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
	DbmApiMetadata                APIConfig `yaml:"dbmApiMetadata"`
	DbmApiUpdateStatus            APIConfig `yaml:"dbmApiUpdateStatus"`
	DbmApiSwapMysqlRole           APIConfig `yaml:"dbmApiSwapMysqlRole"`
	DbmApiSwapRedisRole           APIConfig `yaml:"dbmApiSwapRedisRole"`
	DbmApiQueryRedisPassword      APIConfig `yaml:"dbmApiQueryRedisPassword"`
	DbmApiDomainGet               APIConfig `yaml:"dbmApiDomainGet"`
	DbmApiDomainPut               APIConfig `yaml:"dbmApiDomainPut"`
	DbmApiDomainDelete            APIConfig `yaml:"dbmApiDomainDelete"`
	DbmApiClbGetTargetPrivateIps  APIConfig `yaml:"dbmApiClbGetTargetPrivateIps"`
	DbmApiClbRegisterPartTarget   APIConfig `yaml:"dbmApiClbRegisterPartTarget"`
	DbmApiClbDeregisterPartTarget APIConfig `yaml:"dbmApiClbDeregisterPartTarget"`
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

func clusterTypeNames(types []haprobe.DbmMetadataClusterType) []string {
	out := make([]string, len(types))
	for i, clusterType := range types {
		out[i] = clusterType.String()
	}
	return out
}
