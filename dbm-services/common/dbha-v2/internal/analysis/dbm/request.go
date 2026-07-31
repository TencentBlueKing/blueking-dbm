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

var DefaultRequest = Request{
	MachineOnly: false,
}

// Request represents the request structure for getting metadata of instances
type Request struct {
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
