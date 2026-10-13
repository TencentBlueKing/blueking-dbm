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
	"reflect"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haredis"

	"go.uber.org/zap"
)

const defaultClusterMaxConcurrency = 20

// ClusterMaxConcurrency controls the maximum number of concurrent goroutines used by cluster tools.
var ClusterMaxConcurrency = defaultClusterMaxConcurrency

func getClusterMaxConcurrency() int {
	if ClusterMaxConcurrency <= 0 {
		return defaultClusterMaxConcurrency
	}
	return ClusterMaxConcurrency
}

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

// ClbBindingInfo represents CLB binding information for a listener.
type ClbBindingInfo struct {
	ClbID        string   `json:"clb_id"`
	ListenerID   string   `json:"listener_id"`
	Region       string   `json:"region"`
	InstanceList []string `json:"instance_list"`
}

// ClusterClbInfo represents all CLB bindings for a cluster.
type ClusterClbInfo struct {
	Cluster string           `json:"cluster"`
	ClbList []ClbBindingInfo `json:"clb_list"`
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

// RedisReplicationInfo is one node's INFO replication, using redis field names.
type RedisReplicationInfo struct {
	IP               string `json:"ip"`
	Port             int    `json:"port"`
	Role             string `json:"role"`
	MasterIP         string `json:"master_ip"`
	MasterPort       int    `json:"master_port"`
	MasterLinkStatus string `json:"master_link_status"`
}

// ClusterRedisReplicationInfo represents INFO replication of every storage node in a cluster.
type ClusterRedisReplicationInfo struct {
	Cluster      string                 `json:"cluster"`
	Replications []RedisReplicationInfo `json:"replications"`
}

// ClusterRedisClusterNodesInfo represents CLUSTER NODES of one redis cluster-protocol cluster.
type ClusterRedisClusterNodesInfo struct {
	Cluster     string                `json:"cluster"`
	QueriedFrom string                `json:"queried_from"`
	Nodes       []haredis.ClusterNode `json:"nodes"`
}

// TenDBRoutingEntry represents a single routing entry from mysql.servers
type TenDBRoutingEntry struct {
	ServerName string `json:"server_name" gorm:"column:Server_name"`
	Host       string `json:"host" gorm:"column:Host"`
	Port       int    `json:"port" gorm:"column:Port"`
	Username   string `json:"username" gorm:"column:Username"`
	Wrapper    string `json:"wrapper" gorm:"column:Wrapper"`
}

// TenDBRoutingInfo represents TenDBCluster routing table with check result
type TenDBRoutingInfo struct {
	Cluster     string              `json:"cluster"`
	Routing     []TenDBRoutingEntry `json:"routing"`
	CheckResult string              `json:"check_result"`
}

// MysqlProxyBackend represents a single backend entry for a mysql proxy
type MysqlProxyBackend struct {
	BackendNdx   int    `json:"backend_ndx"`
	BackendAddr  string `json:"backend_addr"`
	BackendState string `json:"backend_state"`
}

// MysqlProxyRouting represents routing information for a single mysql proxy
type MysqlProxyRouting struct {
	ProxyIP        string              `json:"proxy_ip"`
	ProxyAdminPort int                 `json:"proxy_admin_port"`
	Backends       []MysqlProxyBackend `json:"backends"`
}

// MysqlRoutingInfo represents MySQL cluster proxy routing information grouped by cluster
type MysqlRoutingInfo struct {
	Cluster string              `json:"cluster"`
	Proxies []MysqlProxyRouting `json:"proxies"`
}

// TwemproxyBackend represents one twemproxy hash segment and its backend.
type TwemproxyBackend struct {
	Segment string `json:"segment"`
	Address string `json:"address"`
}

// TwemproxyProxyRouting represents routing information for a single twemproxy.
type TwemproxyProxyRouting struct {
	ProxyIP        string             `json:"proxy_ip"`
	ProxyAdminPort int                `json:"proxy_admin_port"`
	MD5            string             `json:"md5"`
	Backends       []TwemproxyBackend `json:"backends"`
}

// TwemproxyRoutingInfo represents twemproxy backends of one redis cluster with check result.
type TwemproxyRoutingInfo struct {
	Cluster     string                  `json:"cluster"`
	Routing     []TwemproxyProxyRouting `json:"routing"`
	CheckResult string                  `json:"check_result"`
}

// PredixyRoutingServer is one backend entry exposed by show routing.
// MD5 is computed from Slot and Server. Slot is empty when Predixy does not report it yet.
type PredixyRoutingServer struct {
	Server        string `json:"server"`
	Slot          string `json:"slot"`
	Role          string `json:"role"`
	CurrentIsFail int    `json:"current_is_fail"`
}

// PredixyProxyRouting represents routing information for a single predixy data port.
type PredixyProxyRouting struct {
	ProxyIP   string                 `json:"proxy_ip"`
	ProxyPort int                    `json:"proxy_port"`
	MD5       string                 `json:"md5"`
	Servers   []PredixyRoutingServer `json:"servers"`
}

// PredixyRoutingInfo represents Predixy INFO Servers of one redis cluster with check result.
type PredixyRoutingInfo struct {
	Cluster     string                `json:"cluster"`
	Routing     []PredixyProxyRouting `json:"routing"`
	CheckResult string                `json:"check_result"`
}

// ProcesslistEntry represents a row of information_schema.processlist
type ProcesslistEntry struct {
	ID      int64   `json:"id"      gorm:"column:ID"`
	User    string  `json:"user"    gorm:"column:USER"`
	Host    string  `json:"host"    gorm:"column:HOST"`
	DB      *string `json:"db"      gorm:"column:DB"`
	Command string  `json:"command" gorm:"column:COMMAND"`
	Time    int64   `json:"time"    gorm:"column:TIME"`
	State   *string `json:"state"   gorm:"column:STATE"`
	Info    *string `json:"info"    gorm:"column:INFO"`
}

// InstanceSessionInfo represents the processlist of a single instance; Result and Errmsg are always present
type InstanceSessionInfo struct {
	IP       string             `json:"ip"`
	Port     int                `json:"port"`
	Result   bool               `json:"result"`
	Errmsg   string             `json:"errmsg"`
	Total    int                `json:"total"`
	Sessions []ProcesslistEntry `json:"sessions"`
}

// ClusterSessionInfo represents the processlist of all instances in a cluster
type ClusterSessionInfo struct {
	Cluster   string                `json:"cluster"`
	Instances []InstanceSessionInfo `json:"instances"`
}

// sessionNodeTarget describes one node to query; tdbctl marks nodes needing a tdbctl-compatible DSN
type sessionNodeTarget struct {
	host     string
	port     int
	user     string
	password string
	tdbctl   bool
}

// ShowResponse represents the standard response format for show commands
type ShowResponse struct {
	Result bool        `json:"result"`
	Errmsg string      `json:"errmsg"`
	Data   interface{} `json:"data"`
}

type silentGormLogger struct{}

func (silentGormLogger) OriginLogger() *zap.Logger { return zap.NewNop() }
func (silentGormLogger) Debug(string, ...any)      {}
func (silentGormLogger) Info(string, ...any)       {}
func (silentGormLogger) Warn(string, ...any)       {}
func (silentGormLogger) Error(string, ...any)      {}
func (silentGormLogger) Fatal(string, ...any)      {}

var toolsGormLogger logger.Logger = silentGormLogger{}

func newToolGormDB(opts ...hamysql.Option) (*hamysql.GormDB, error) {
	opts = append(opts, hamysql.OptionLogger(toolsGormLogger))
	return hamysql.NewGormDB(opts...)
}

// printJSON prints data in JSON format with result and errmsg fields
func printJSON(data interface{}) error {
	return printShowResponse(true, "", data)
}

func printCollectedJSON[T any](data []T, err error) error {
	if err == nil {
		return printJSON(data)
	}
	if isNotImplemented(err) {
		return printShowResponse(false, err.Error(), data)
	}
	return printErrorResponse(err.Error())
}

func collectSlices[T any](handlers []ClusterHandler, fn func(ClusterHandler) ([]T, error), command string) ([]T, error) {
	out := make([]T, 0)
	sawUnimplemented := false
	for _, hdl := range handlers {
		data, err := fn(hdl)
		if isNotImplemented(err) {
			sawUnimplemented = true
			continue
		}
		if err != nil {
			return nil, err
		}
		out = append(out, data...)
	}
	if sawUnimplemented {
		return out, unimplemented(command)
	}
	return out, nil
}

func flattenToAny(data any) []any {
	if data == nil {
		return nil
	}

	value := reflect.ValueOf(data)
	if value.Kind() != reflect.Slice {
		return []any{data}
	}

	out := make([]any, 0, value.Len())
	for i := 0; i < value.Len(); i++ {
		out = append(out, value.Index(i).Interface())
	}
	return out
}

func collectAnySlices(handlers []ClusterHandler, fn func(ClusterHandler) (any, error), command string) ([]any, error) {
	out := make([]any, 0)
	sawUnimplemented := false
	for _, hdl := range handlers {
		data, err := fn(hdl)
		if isNotImplemented(err) {
			sawUnimplemented = true
			continue
		}
		if err != nil {
			return nil, err
		}
		out = append(out, flattenToAny(data)...)
	}
	if sawUnimplemented {
		return out, unimplemented(command)
	}
	return out, nil
}

// PrintShowDomain prints one JSON document for every selected handler's domain info.
func PrintShowDomain(handlers []ClusterHandler) error {
	return printCollectedJSON(collectSlices(handlers, ClusterHandler.ShowDomain, "show domain"))
}

// PrintShowNodes prints one JSON document for every selected handler's node info.
func PrintShowNodes(handlers []ClusterHandler) error {
	return printCollectedJSON(collectSlices(handlers, ClusterHandler.ShowNodes, "show nodes"))
}

// PrintShowClb prints one JSON document for every selected handler's CLB info.
func PrintShowClb(handlers []ClusterHandler) error {
	return printCollectedJSON(collectSlices(handlers, ClusterHandler.ShowClb, "show clb"))
}

// PrintShowReplication prints one JSON document for every selected handler's replication info.
func PrintShowReplication(handlers []ClusterHandler) error {
	return printCollectedJSON(collectAnySlices(handlers, ClusterHandler.ShowReplication, "show replication"))
}

// PrintShowRouting prints one JSON document for every selected handler's routing info.
func PrintShowRouting(handlers []ClusterHandler) error {
	return printCollectedJSON(collectAnySlices(handlers, ClusterHandler.ShowRouting, "show routing"))
}

// PrintShowSession prints one JSON document for every selected handler's sessions.
func PrintShowSession(handlers []ClusterHandler, where string) error {
	data, err := collectSlices(handlers, func(hdl ClusterHandler) ([]ClusterSessionInfo, error) {
		return hdl.ShowSession(where)
	}, "show session")
	if err != nil && !isNotImplemented(err) {
		return printErrorResponse(err.Error())
	}
	extraErrmsg := ""
	if err != nil {
		extraErrmsg = err.Error()
	}
	return printSessionJSON(data, extraErrmsg)
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
