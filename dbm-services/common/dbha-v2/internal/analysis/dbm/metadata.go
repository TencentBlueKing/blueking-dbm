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

package dbm

// the "status" in metadata.
type DbmMetadataStatus string

const (
	RUNNING     DbmMetadataStatus = "running"
	UNAVAILABLE DbmMetadataStatus = "unavailable"
	AVAILABLE   DbmMetadataStatus = "available"
)

// the "instance_role" in metadata.
type DbmMetadataInstanceRole string

const (
	// mysql instance role
	MySQLStorageMaster   DbmMetadataInstanceRole = "backend_master"
	MySQLStorageSlave    DbmMetadataInstanceRole = "backend_slave"
	MySQLStorageRepeater DbmMetadataInstanceRole = "backend_repeater"

	// tendbcluster instance role
	TenDBClusterStorageMaster DbmMetadataInstanceRole = "remote_master"
	TenDBClusterStorageSlave  DbmMetadataInstanceRole = "remote_slave"
	TenDBClusterProxyMaster   DbmMetadataInstanceRole = "spider_master"
	TenDBClusterProxySlave    DbmMetadataInstanceRole = "spider_slave"
)

// the "spider_role" in metadata.
type DbmMetadataSpiderRole string

const (
	TenDBClusterSpiderMaster DbmMetadataSpiderRole = "spider_master"
	TenDBClusterSpiderSlave  DbmMetadataSpiderRole = "spider_slave"
)

// DbmMetadataSlaveInfo defined "receiver" info in metadata.
type DbmMetadataSlaveInfo struct {
	Ip        string            `json:"ip"`
	Port      int               `json:"port"`
	IsStandBy bool              `json:"is_stand_by"`
	Status    DbmMetadataStatus `json:"status"`
}

// BindEntryPolarisInfo defined "polaris" info of "bind_entry" in metadata.
type BindEntryPolarisInfo struct {
	Service string `json:"polaris_name"`
	Token   string `json:"polaris_token"`
	L5      string `json:"polaris_l5"`
	// the ip list bind to clb
	BindIps  []string `json:"bind_ips"`
	BindPort int      `json:"bind_port"`
}

// BindEntryClbInfo defined "clb" info of "bind_entry" in metadata.
type BindEntryClbInfo struct {
	Region        string `json:"clb_region"`
	LoadBalanceId string `json:"clb_id"`
	ListenId      string `json:"listener_id"`
	Ip            string `json:"clb_ip"`

	// the ip list bind to clb
	BindIps  []string `json:"bind_ips"`
	BindPort int      `json:"bind_port"`
}

// BindEntryDnsInfo defined "dns" info of "bind_entry" in metadata.
type BindEntryDnsInfo struct {
	DomainName     string   `json:"domain"`
	EntryRole      string   `json:"entry_role"`
	BindIps        []string `json:"bind_ips"`
	BindPort       int      `json:"bind_port"`
	ForwardEntryId int      `json:"forward_entry_id"`
}

// DbmMetadataBindEntry defined "bind_entry" info in metadata.
type DbmMetadataBindEntry struct {
	DNS     []BindEntryDnsInfo
	Polaris []BindEntryPolarisInfo
	CLB     []BindEntryClbInfo
}

// DbmMetadataProxyInstance defined "proxyinstance" info in metadata.
type DbmMetadataProxyInstance struct {
	Ip        string            `json:"ip"`
	Port      int               `json:"port"`
	AdminPort int               `json:"admin_port"`
	Status    DbmMetadataStatus `json:"status"`
}

// DbmMetadataBinlogDumper defined "tbinlogdumper" info in metadata.
type DbmMetadataBinlogDumper struct {
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}
