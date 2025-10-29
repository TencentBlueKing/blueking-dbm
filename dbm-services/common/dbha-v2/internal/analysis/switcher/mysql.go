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

package switcher

import (
	"context"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ErrMySqlPartialSuccess = gerrors.Newf(gerrors.Failure, "the switching achieved partial success")
)

var _ Switcher = (*Mysql)(nil)

// Mysql implements the Switcher interface for MySQL database instances
type Mysql struct {
}

// DbTypeName returns the MySQL database type identifier
func (m *Mysql) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeMysql
}

// Switch handles MySQL instance switching operations
// Note: This function may be called concurrently, avoid unnecessary duplicate switching
// Note: For TenDBCluster, handle partial switch failures when multiple instances on same host
func (m *Mysql) Switch(ctx context.Context, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[MetadataKey]*MySQLInstanceMetadata{},
	}

	for _, inst := range req.MySqlInstData {
		instKey := GenerateMetadataKey(inst.BkCloudID, inst.Ip, inst.Port)
		swInst, newErr := NewMySQLSwitchInstance(inst)

		if newErr != nil {
			logger.Warn("failed to create mysql switcher, inst: %s, errmsg: %s", instKey, newErr)
			rsp.MySqlFailureInsts[instKey] = inst
			continue
		}

		success, swErr := SwitchSingleInstance(swInst)
		if success {
			logger.Info("successfully switched the single instance: %s", instKey)

			continue
		}

		logger.Warn("failed to switch the single instance: %s, errmsg: %s", instKey, swErr)
		rsp.MySqlFailureInsts[instKey] = inst
	}

	if len(rsp.MySqlFailureInsts) == 0 {
		return rsp
	}

	rsp.Err = ErrMySqlPartialSuccess
	return rsp
}
