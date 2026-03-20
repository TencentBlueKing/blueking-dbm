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

package handler

import (
	"encoding/json"
	"fmt"
)

// DomainInstanceList represents instance list for a specific domain
type DomainInstanceList struct {
	Domain       string   `json:"domain"`
	InstanceList []string `json:"instance_list"`
}

// ClusterDomainInfo represents all domain bindings for a cluster
type ClusterDomainInfo struct {
	Cluster string               `json:"cluster"`
	Domains []DomainInstanceList `json:"domains"`
}

// NodeInfo represents node status and role information
type NodeInfo struct {
	ServerName string `json:"server_name,omitempty"`
	IP         string `json:"ip"`
	Port       int    `json:"port"`
	Status     string `json:"status"`
	Role       string `json:"role"`
}

// ClusterNodeInfo represents all nodes for a cluster
type ClusterNodeInfo struct {
	Cluster string     `json:"cluster"`
	Nodes   []NodeInfo `json:"nodes"`
}

// ReplicationInfo represents master-slave replication status
type ReplicationInfo struct {
	ServerName      string `json:"server_name,omitempty"`
	IP              string `json:"ip"`
	Port            int    `json:"port"`
	MasterIP        string `json:"master_ip"`
	MasterPort      int    `json:"master_port"`
	SlaveIORunning  string `json:"slave_io_running"`
	SlaveSQLRunning string `json:"slave_sql_running"`
}

// ClusterReplicationInfo represents all replication status for a cluster
type ClusterReplicationInfo struct {
	Cluster      string            `json:"cluster"`
	Replications []ReplicationInfo `json:"replications"`
}

// RoutingEntry represents a single routing entry from mysql.servers
type RoutingEntry struct {
	ServerName string `json:"server_name" gorm:"column:Server_name"`
	Host       string `json:"host" gorm:"column:Host"`
	Port       int    `json:"port" gorm:"column:Port"`
	Username   string `json:"username" gorm:"column:Username"`
	Wrapper    string `json:"wrapper" gorm:"column:Wrapper"`
}

// ClusterRoutingInfo represents TenDBCluster routing table with check result
type ClusterRoutingInfo struct {
	Cluster     string         `json:"cluster"`
	Routing     []RoutingEntry `json:"routing"`
	CheckResult string         `json:"check_result"`
}

// ProxyBackendEntry represents a single backend entry for a proxy
type ProxyBackendEntry struct {
	BackendNdx   int    `json:"backend_ndx"`
	BackendAddr  string `json:"backend_addr"`
	BackendState string `json:"backend_state"`
}

// ProxyRoutingEntry represents routing information for a single proxy
type ProxyRoutingEntry struct {
	ProxyIP        string              `json:"proxy_ip"`
	ProxyAdminPort int                 `json:"proxy_admin_port"`
	Backends       []ProxyBackendEntry `json:"backends"`
}

// ClusterProxyRoutingInfo represents MySQL cluster proxy routing information grouped by cluster
type ClusterProxyRoutingInfo struct {
	Cluster string              `json:"cluster"`
	Proxies []ProxyRoutingEntry `json:"proxies"`
}

// ShowResponse represents the standard response format for show commands
type ShowResponse struct {
	Result bool        `json:"result"`
	Errmsg string      `json:"errmsg"`
	Data   interface{} `json:"data"`
}

// printJSON prints data in JSON format with result and errmsg fields
func printJSON(data interface{}) error {
	return printShowResponse(true, "", data)
}

// printShowResponse prints response with result, errmsg and data
func printShowResponse(result bool, errmsg string, data interface{}) error {
	response := ShowResponse{
		Result: result,
		Errmsg: errmsg,
		Data:   data,
	}

	jsonData, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		errResponse := ShowResponse{
			Result: false,
			Errmsg: fmt.Sprintf("failed to marshal JSON, errmsg: %s", err.Error()),
			Data:   nil,
		}
		errJsonData, _ := json.MarshalIndent(errResponse, "", "  ")
		fmt.Println(string(errJsonData))
		return nil
	}

	fmt.Println(string(jsonData))
	return nil
}

// printErrorResponse prints error response and returns nil (no error)
func printErrorResponse(errmsg string) error {
	return printShowResponse(false, errmsg, nil)
}

// printErrorResponsef prints formatted error response and returns nil (no error)
func printErrorResponsef(format string, args ...interface{}) error {
	return printShowResponse(false, fmt.Sprintf(format, args...), nil)
}
