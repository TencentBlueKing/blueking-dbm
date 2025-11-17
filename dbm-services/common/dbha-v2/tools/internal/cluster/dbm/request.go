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
	MachineOnly: true,
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
