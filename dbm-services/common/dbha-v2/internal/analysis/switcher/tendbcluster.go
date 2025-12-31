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

	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// TendbCluster implements the Switcher interface for TenDBCluster database instances
type TendbCluster struct {
}

// DbTypeName returns the TenDBCluster database type identifier
func (m *TendbCluster) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeTendbCluster
}

// Switch handles TenDBCluster instance switching operations
// Note: This function may be called concurrently, avoid unnecessary duplicate switching
// Note: Handle partial switch failures when multiple instances on same host
func (m *TendbCluster) Switch(ctx context.Context, req *Request) *Response {
	rsp := &Response{
		TendbClusterFailureInsts: map[MetadataKey]*TendbClusterInstanceMetadata{},
	}

	if req == nil {
		rsp.Err = gerrors.Newf(gerrors.Failure, "TendbCluster switcher get nil request")
		return rsp
	}

	switchLogger, newLoggerErr := switchlogger.NewLogToDbHandlerFromConfig()
	if newLoggerErr != nil {
		rsp.Err = gerrors.Newf(gerrors.Failure,
			"Tendbcluster switcher failed to create switch logger: %s", newLoggerErr)
		return rsp
	}

	if err := switchLogger.Open(); err != nil {
		rsp.Err = gerrors.Newf(gerrors.Failure,
			"Tendbcluster switcher failed to open switch logger: %s", err)
		return rsp
	}
	defer switchLogger.Close()

	for _, inst := range req.TendbClusterInstData {
		if inst == nil {
			logger.Warn("TendbCluster switcher get nil instance")
			continue
		}

		instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		swInst, newErr := NewTendbClusterSwitchInstance(inst)

		if newErr != nil {
			logger.Warn("failed to create TenDBCluster switcher, inst: %s, errmsg: %s", instKey, newErr)
			rsp.TendbClusterFailureInsts[instKey] = inst
			continue
		}

		swInst.SetSwitchLogger([]switchlogger.DbSwitchLogger{
			switchLogger,
			switchlogger.NewLogToStdHandler(),
		})

		logger.Info("start to switch the single tendbcluster instance: %s", instKey)
		if swErr := SwitchSingleInstance(swInst); swErr != nil {
			logger.Warn("failed to switch the single tendbcluster instance: %s, errmsg: %s", instKey, swErr)
			rsp.TendbClusterFailureInsts[instKey] = inst
			continue
		}
		logger.Info("successfully switched the single tendbcluster instance: %s", instKey)
	}

	if len(rsp.TendbClusterFailureInsts) == 0 {
		return rsp
	}

	rsp.Err = ErrSwitchPartialSuccess
	return rsp
}
