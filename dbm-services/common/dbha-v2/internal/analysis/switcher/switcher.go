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
	"dbm-services/common/dbha-v2/pkg/logger"
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

// AddDbInstMetadata adds database instance metadata to the appropriate list based on cluster type
func (req *Request) AddDbInstMetadata(metadata *MySQLInstanceMetadata) {
	logger.Info("AddDbInstMetadata: IP=%s, Port=%d, ClusterType=%s, MachineType=%s, isTendbCluster=%v, isSpider=%v",
		metadata.IP, metadata.Port, metadata.ClusterType, metadata.MachineType,
		metadata.ClusterType == haprobe.DbmMetadataClusterTypeTendbCluster,
		metadata.MachineType == haprobe.DbmMetadataMachineTypeSpider)

	if metadata.ClusterType == haprobe.DbmMetadataClusterTypeTendbCluster ||
		metadata.MachineType == haprobe.DbmMetadataMachineTypeSpider {
		req.TendbClusterInstData = append(req.TendbClusterInstData, (*TendbClusterInstanceMetadata)(metadata))
	} else {
		req.MySqlInstData = append(req.MySqlInstData, metadata)
	}
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
