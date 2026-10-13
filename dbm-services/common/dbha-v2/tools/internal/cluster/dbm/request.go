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

var DefaultMetadataRequest = MetadataRequest{
	MachineOnly: false,
}

// MetadataRequest represents the request structure for getting metadata of instances
type MetadataRequest struct {
	BkCloudId      int      `json:"bk_cloud_id"`
	DbCloudToken   string   `json:"db_cloud_token"`
	Addresses      []string `json:"addresses"`
	LogicalCityIDs []string `json:"logical_city_ids,omitempty"`
	Statuses       []string `json:"statuses,omitempty"`
	ClusterTypes   []string `json:"cluster_types,omitempty"`
	HashCnt        int      `json:"hash_cnt,omitempty"`
	HashValue      int      `json:"hash_value,omitempty"`
	MachineOnly    bool     `json:"machine_only,omitempty"`
}

// SwapMySQLRoleInstance represents a single MySQL instance for role swapping
type SwapMySQLRoleInstance struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapMySQLRolePayload contains two instances for MySQL role swapping
// Note: instance1 and instance2 should be a MySQL master-slave pair.
// While there is no need to distinguish which is master and which is slave.
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

// SwapRedisRoleInstance represents a single Redis instance for role swapping
type SwapRedisRoleInstance struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapRedisRolePayload contains the master-slave pair and cluster domain for role swapping.
// Note: master and slave should be a Redis master-slave pair.
// master should be the current redis master, slave should be the current redis slave.
type SwapRedisRolePayload struct {
	Master SwapRedisRoleInstance `json:"master"`
	Slave  SwapRedisRoleInstance `json:"slave"`
	Domain string                `json:"domain"`
}

// SwapRedisRoleRequest represents the request for swapping Redis master-slave roles.
// Payload is a single object, not an array.
type SwapRedisRoleRequest struct {
	BkCloudID    int                  `json:"bk_cloud_id"`
	DbCloudToken string               `json:"db_cloud_token"`
	Payload      SwapRedisRolePayload `json:"payload"`
}

// DomainGetRequest represents the request structure for getting domain information
type DomainGetRequest struct {
	BkCloudID    int      `json:"bk_cloud_id"`
	DbCloudToken string   `json:"db_cloud_token"`
	DomainName   []string `json:"domain_name"`
}

// InstancesOfDomain contains domain name and its associated instances
type InstancesOfDomain struct {
	DomainName string   `json:"domain_name"`
	Instances  []string `json:"instances"`
}

// DomainPutRequest represents the request structure for adding instances to a domain
type DomainPutRequest struct {
	App            string              `json:"app"`
	BkCloudID      int                 `json:"bk_cloud_id"`
	DbCloudToken   string              `json:"db_cloud_token"`
	InstancesToAdd []InstancesOfDomain `json:"domains"`
}

// DomainDeleteRequest represents the request structure for deleting instances from a domain
type DomainDeleteRequest struct {
	App               string              `json:"app"`
	BkCloudID         int                 `json:"bk_cloud_id"`
	DbCloudToken      string              `json:"db_cloud_token"`
	InstancesToDelete []InstancesOfDomain `json:"domains"`
}

// ClbGetTargetPrivateIpsRequest represents the request for querying CLB bound instances.
type ClbGetTargetPrivateIpsRequest struct {
	BkCloudID      int    `json:"bk_cloud_id"`
	DbCloudToken   string `json:"db_cloud_token"`
	Region         string `json:"region"`
	ListenerID     string `json:"listenerid"`
	LoadBalancerID string `json:"loadbalancerid"`
}

// ClbRegisterPartTargetRequest represents the request for registering instances to CLB.
type ClbRegisterPartTargetRequest struct {
	BkCloudID      int      `json:"bk_cloud_id"`
	DbCloudToken   string   `json:"db_cloud_token"`
	Region         string   `json:"region"`
	ListenerID     string   `json:"listenerid"`
	LoadBalancerID string   `json:"loadbalancerid"`
	IPs            []string `json:"ips"`
}

// ClbDeregisterPartTargetRequest represents the request for deregistering instances from CLB.
type ClbDeregisterPartTargetRequest struct {
	BkCloudID      int      `json:"bk_cloud_id"`
	DbCloudToken   string   `json:"db_cloud_token"`
	Region         string   `json:"region"`
	ListenerID     string   `json:"listenerid"`
	LoadBalancerID string   `json:"loadbalancerid"`
	IPs            []string `json:"ips"`
}

// passwdInstance selects one instance of the password service. Redis cluster
// credentials are stored per cluster, with the cluster id sitting in the ip field.
type passwdInstance struct {
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	BkCloudID int    `json:"bk_cloud_id"`
}

// passwdUser selects which credential of an instance to read.
type passwdUser struct {
	UserName  string `json:"username"`
	Component string `json:"component"`
}

// QueryPasswdRequest is the body of one password query.
type QueryPasswdRequest struct {
	DbCloudToken string           `json:"db_cloud_token"`
	BkCloudID    int              `json:"bk_cloud_id"`
	Instances    []passwdInstance `json:"instances"`
	Users        []passwdUser     `json:"users"`
	Limit        int              `json:"limit"`
}
