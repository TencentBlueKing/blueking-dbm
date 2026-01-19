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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type MetadataKey string

var (
	ErrSwitchPartialSuccess = gerrors.Newf(gerrors.Failure, "the switching achieved partial success")
)

// Request contains all data needed for database switching operation
type Request struct {
	ActionScope   hamodel.ActionScopeType
	DbType        haprobe.DbType
	MySqlInstData []*MysqlInstanceMetadata
}

// AddDbInstMetadata TODO: Need to adapt to different types of DB instance data
func (req *Request) AddDbInstMetadata(metadata *MysqlInstanceMetadata) {
	req.MySqlInstData = append(req.MySqlInstData, metadata)
}

// HasDbInstMetadata checks if there is any database instance data
func (req *Request) HasDbInstMetadata() bool {
	return len(req.MySqlInstData) > 0
}

// GetDbInstMetadata gets all database instance data
func (req *Request) GetDbInstMetadata() []*dbm.DbInstMetadata {
	if req.MySqlInstData == nil {
		return nil
	}

	datas := []*dbm.DbInstMetadata{}
	for _, inst := range req.MySqlInstData {
		datas = append(datas, (*dbm.DbInstMetadata)(inst))
	}

	return datas
}

// Response contains the result of switching operation
type Response struct {
	MySqlFailureInsts map[MetadataKey]*MysqlInstanceMetadata
	Err               error
}

// GetFailureInsts gets the failed instances
func (rsp *Response) GetFailureInsts() map[MetadataKey]*dbm.DbInstMetadata {
	if rsp.MySqlFailureInsts == nil {
		return nil
	}

	insts := map[MetadataKey]*dbm.DbInstMetadata{}

	for k, v := range rsp.MySqlFailureInsts {
		insts[k] = (*dbm.DbInstMetadata)(v)
	}

	return insts
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
