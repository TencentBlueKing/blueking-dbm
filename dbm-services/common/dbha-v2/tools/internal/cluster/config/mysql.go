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

import "dbm-services/common/dbha-v2/pkg/storage/haprobe"

// MysqlCluster represents a MySQL cluster.
type MysqlCluster struct {
	Domain      string            `yaml:"domain"`
	DomainSlave string            `yaml:"domainSlave"`
	BkBizId     int               `yaml:"bkBizId"`
	Proxy       []ProxyAddress    `yaml:"proxy"`
	Master      InstanceAddress   `yaml:"master"`
	Slave       []InstanceAddress `yaml:"slave"`
	Clb         []ClbConfig       `yaml:"clb,omitempty"`
}

// TenDBClusterNodeInfo represents the information of a TenDBCluster node.
type TenDBClusterNodeInfo struct {
	Host       string `yaml:"host"`
	Port       int    `yaml:"port"`
	ServerName string `yaml:"serverName"`
	User       string `yaml:"user"`
	Password   string `yaml:"password"`
	Wrapper    string
}

// RemoteSlaveInfo represents the information of a remote slave instance.
type RemoteSlaveInfo struct {
	TenDBClusterNodeInfo `yaml:",inline"`
	MasterHost           string `yaml:"masterHost"`
	MasterPort           int    `yaml:"masterPort"`
}

// TenDBCluster represents a TenDB cluster.
type TenDBCluster struct {
	Domain       string                 `yaml:"domain"`
	DomainSlave  string                 `yaml:"domainSlave"`
	BkBizId      int                    `yaml:"bkBizId"`
	Spider       []TenDBClusterNodeInfo `yaml:"spider"`
	SpiderSlave  []TenDBClusterNodeInfo `yaml:"spiderSlave"`
	CtlMaster    TenDBClusterNodeInfo   `yaml:"ctlMaster"`
	CtlSlave     []TenDBClusterNodeInfo `yaml:"ctlSlave"`
	RemoteMaster []TenDBClusterNodeInfo `yaml:"remoteMaster"`
	RemoteSlave  []RemoteSlaveInfo      `yaml:"remoteSlave"`
	Clb          []ClbConfig            `yaml:"clb,omitempty"`
}

var mysqlClusterTypes = []haprobe.DbmMetadataClusterType{
	ClusterTypeTendbha,
	ClusterTypeTendbCluster,
}
