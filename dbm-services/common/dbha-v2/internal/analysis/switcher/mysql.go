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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ Switcher = (*Mysql)(nil)

// MysqlInstanceMetadata contains MySQL instance metadata from DBM
type MysqlInstanceMetadata dbm.DbInstMetadata

// Mysql implements the Switcher interface for MySQL database instances
type Mysql struct {
}

// DbTypeName returns the MySQL database type identifier
func (m *Mysql) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeMySql
}

// NewSwitchInstance creates a MySQL switch instance according to the provided metadata
func (m *Mysql) NewSwitchInstance(metadata *MysqlInstanceMetadata) (SwitchableInstance, error) {
	switch metadata.ClusterType {
	case haprobe.DbmMetadataClusterTypeTendbha:
		return NewMySQLSwitchInstance(metadata)
	case haprobe.DbmMetadataClusterTypeTendbCluster:
		return NewTendbClusterSwitchInstance(metadata)
	default:
		return nil, gerrors.Newf(gerrors.Failure, "unsupported cluster type: %s", metadata.ClusterType)
	}
}

// NewSwitchLogger creates mysql switch logger set
func (m *Mysql) NewSwitchLogger() ([]switchlogger.DbSwitchLogger, error) {
	loggers := []switchlogger.DbSwitchLogger{
		switchlogger.NewLogToStdHandler(),
	}

	dbHdl, newDbHdlErr := switchlogger.NewLogToDbHandlerFromConfig()
	if newDbHdlErr != nil {
		return loggers, gerrors.Newf(gerrors.Failure, "failed to create db switch logger: %s", newDbHdlErr.Error())
	}

	if openErr := dbHdl.Open(); openErr != nil {
		return loggers, gerrors.Newf(gerrors.Failure, "failed to open db switch logger: %s", openErr.Error())
	}

	loggers = append(loggers, dbHdl)
	return loggers, nil
}

// Switch handles MySQL instance switching operations
// Note: This function may be called concurrently, avoid unnecessary duplicate switching
// Note: Handle partial switch failures when multiple instances on same host
func (m *Mysql) Switch(ctx context.Context, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[MetadataKey]*MysqlInstanceMetadata{},
	}

	if req == nil {
		rsp.Err = gerrors.Newf(gerrors.Failure, "Mysql switcher get nil request")
		return rsp
	}

	switchLoggers, newLoggerErr := m.NewSwitchLogger()
	if newLoggerErr != nil {
		logger.Error("Mysql switcher failed to create switch logger: %s", newLoggerErr)
	}

	defer func() {
		for _, switchLogger := range switchLoggers {
			switchLogger.Close()
		}
	}()

	for _, inst := range req.MySqlInstData {
		if inst == nil {
			logger.Warn("Mysql switcher get nil instance")
			continue
		}

		instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		swInst, newErr := m.NewSwitchInstance(inst)
		if newErr != nil {
			logger.Warn("failed to create mysql switcher, inst: %s, errmsg: %s", instKey, newErr)
			rsp.MySqlFailureInsts[instKey] = inst
			continue
		}

		swInst.SetSwitchLogger(switchLoggers)

		logger.Info("start to switch the single mysql instance: %s", instKey)
		if swErr := SwitchSingleInstance(swInst); swErr != nil {
			logger.Warn("failed to switch the single mysql instance: %s, errmsg: %s", instKey, swErr)
			rsp.MySqlFailureInsts[instKey] = inst
			continue
		}
		logger.Info("successfully switched the single mysql instance: %s", instKey)
	}

	if len(rsp.MySqlFailureInsts) == 0 {
		return rsp
	}

	rsp.Err = ErrSwitchPartialSuccess
	return rsp
}
