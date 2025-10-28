/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of sw software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and sw permission notice shall be included in all
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

package switcher

// DomainGetRequest represents the request structure for getting domain information
type DomainGetRequest struct {
	BkCloudID    int    `json:"bk_cloud_id"`
	DbCloudToken string `json:"db_cloud_token"`
	DomainName   string `json:"domain_name"`
}

// InstancesOfDomain contains domain name and its associated instances
type InstancesOfDomain struct {
	DomainName string   `json:"domain_name"`
	Instances  []string `json:"instances"`
}

// DomainDeleteRequest represents the request for deleting instances from domain
type DomainDeleteRequest struct {
	BkCloudID         int                 `json:"bk_cloud_id"`
	DbCloudToken      string              `json:"db_cloud_token"`
	App               string              `json:"app"`
	InstancesToDelete []InstancesOfDomain `json:"domains"`
}

// ClbDeleteRequest represents the request for deregistering from Cloud Load Balancer
type ClbDeleteRequest struct {
	BkCloudID      int      `json:"bk_cloud_id"`
	DbCloudToken   string   `json:"db_cloud_token"`
	Region         string   `json:"region"`
	LoadBalancerID string   `json:"loadbalancerid"`
	ListenerID     string   `json:"listenerid"`
	IPs            []string `json:"ips"`
}

// PolarisDeleteRequest represents the request for unbinding from Polaris service discovery
type PolarisDeleteRequest struct {
	BkCloudID    int      `json:"bk_cloud_id"`
	DbCloudToken string   `json:"db_cloud_token"`
	ServiceName  string   `json:"servicename"`
	ServiceToken string   `json:"servicetoken"`
	IPs          []string `json:"ips"`
}

// SwapMySQLRoleInstance represents a single MySQL instance for role swapping
type SwapMySQLRoleInstance struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapMySQLRolePayload contains two instances for MySQL role swapping
type SwapMySQLRolePayload struct {
	Instance1 SwapMySQLRoleInstance `json:"instance1"`
	Instance2 SwapMySQLRoleInstance `json:"instance2"`
}

// SwapMySQLRoleRequest represents the request for swapping MySQL master-slave roles
type SwapMySQLRoleRequest struct {
	BkCloudID    int                    `json:"bk_cloud_id"`
	DbCloudToken string                 `json:"db_cloud_token"`
	Payloads     []SwapMySQLRolePayload `json:"payloads"`
}

// DumperSwitchInstance represents the instance information for binlog dumper switching
type DumperSwitchInstance struct {
	Ip             string `json:"ip"`
	Port           int    `json:"port"`
	BinlogFile     string `json:"binlog_file"`
	BinlogPosition uint64 `json:"binlog_position"`
}

// DumperSwitchInfo contains cluster domain and dumper instances for switching
type DumperSwitchInfo struct {
	ClusterDomain   string                 `json:"cluster_domain"`
	SwitchInstances []DumperSwitchInstance `json:"switch_instances"`
}

// DumperSwitchRequest represents the request for switching binlog dumper configuration
type DumperSwitchRequest struct {
	BkCloudID    int                `json:"bk_cloud_id"`
	DbCloudToken string             `json:"db_cloud_token"`
	BKBizID      string             `json:"bk_biz_id"`
	IsSafe       bool               `json:"is_safe"`
	SwitchInfos  []DumperSwitchInfo `json:"infos"`
}

// UpdateInstanceStatusPayload contains instance information for status update
type UpdateInstanceStatusPayload struct {
	IP     string `json:"ip"`
	Port   int    `json:"port"`
	Status string `json:"status"`
}

// UpdateInstanceStatusRequest represents the request for updating database instance status
type UpdateInstanceStatusRequest struct {
	BkCloudID    int                           `json:"bk_cloud_id"`
	DbCloudToken string                        `json:"db_cloud_token"`
	Payloads     []UpdateInstanceStatusPayload `json:"payloads"`
}
