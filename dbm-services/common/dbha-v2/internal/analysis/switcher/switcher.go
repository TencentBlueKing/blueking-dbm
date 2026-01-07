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

// Package switcher provides database switching functionality for DBHA
package switcher

import (
	"context"
	"fmt"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type MetadataKey string

var (
	ErrSwitchPartialSuccess = gerrors.Newf(gerrors.Failure, "the switching achieved partial success")
)

// Request contains all data needed for database switching operation
type Request struct {
	MySqlInstData        []*MySQLInstanceMetadata
	TendbClusterInstData []*TendbClusterInstanceMetadata
}

// isTendbClusterInstance checks if the metadata belongs to TendbCluster
func isTendbClusterInstance(metadata *MySQLInstanceMetadata) bool {
	return metadata.ClusterType == haprobe.DbmMetadataClusterTypeTendbCluster
}

// AddDbInstMetadata adds database instance metadata to the appropriate list based on cluster type
func (req *Request) AddDbInstMetadata(metadata *MySQLInstanceMetadata) {
	if isTendbClusterInstance(metadata) {
		req.TendbClusterInstData = append(req.TendbClusterInstData, (*TendbClusterInstanceMetadata)(metadata))
	} else {
		req.MySqlInstData = append(req.MySqlInstData, metadata)
	}
}

// GetDbTypesToSwitch returns the list of database types that need to be switched
func (req *Request) GetDbTypesToSwitch() []haprobe.DbType {
	var dbTypes []haprobe.DbType
	if len(req.MySqlInstData) > 0 {
		dbTypes = append(dbTypes, haprobe.DbTypeMySql)
	}
	if len(req.TendbClusterInstData) > 0 {
		dbTypes = append(dbTypes, haprobe.DbTypeTendbCluster)
	}
	return dbTypes
}

// Response contains the result of switching operation
type Response struct {
	MySqlFailureInsts        map[MetadataKey]*MySQLInstanceMetadata
	TendbClusterFailureInsts map[MetadataKey]*TendbClusterInstanceMetadata
	Err                      error
}

// Switcher defines the interface for database switching implementations
type Switcher interface {
	DbTypeName() haprobe.DbType
	Switch(ctx context.Context, req *Request) *Response
}

// GenerateMetadataKey generates a unique key for instance metadata
func GenerateMetadataKey(bkCloudId int, ip string, port int) MetadataKey {
	return MetadataKey(fmt.Sprintf("%d:%s:%d", bkCloudId, ip, port))
}

// InstanceInfo contains basic instance identification information
type InstanceInfo struct {
	BkCloudID int
	IP        string
	Port      int
}

// GetSuccessInstances returns all successful instances of the specified database type
func (req *Request) GetSuccessInstances(dbType haprobe.DbType, rsp *Response) []InstanceInfo {
	var instances []InstanceInfo
	switch dbType {
	case haprobe.DbTypeMySql:
		for _, inst := range req.MySqlInstData {
			instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
			if _, failed := rsp.MySqlFailureInsts[instKey]; !failed {
				instances = append(instances, InstanceInfo{
					BkCloudID: inst.BkCloudID,
					IP:        inst.IP,
					Port:      inst.Port,
				})
			}
		}
	case haprobe.DbTypeTendbCluster:
		for _, inst := range req.TendbClusterInstData {
			instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
			if _, failed := rsp.TendbClusterFailureInsts[instKey]; !failed {
				instances = append(instances, InstanceInfo{
					BkCloudID: inst.BkCloudID,
					IP:        inst.IP,
					Port:      inst.Port,
				})
			}
		}
	}
	return instances
}

// GetFailureInstances returns all failed instances of the specified database type
func (rsp *Response) GetFailureInstances(dbType haprobe.DbType) []InstanceInfo {
	var instances []InstanceInfo
	switch dbType {
	case haprobe.DbTypeMySql:
		for _, inst := range rsp.MySqlFailureInsts {
			instances = append(instances, InstanceInfo{
				BkCloudID: inst.BkCloudID,
				IP:        inst.IP,
				Port:      inst.Port,
			})
		}
	case haprobe.DbTypeTendbCluster:
		for _, inst := range rsp.TendbClusterFailureInsts {
			instances = append(instances, InstanceInfo{
				BkCloudID: inst.BkCloudID,
				IP:        inst.IP,
				Port:      inst.Port,
			})
		}
	}
	return instances
}
