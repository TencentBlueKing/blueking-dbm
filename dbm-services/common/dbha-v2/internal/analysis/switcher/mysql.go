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
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
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

// InstanceLevelSwitch handles MySQL instance switching operations
func (m *Mysql) InstanceLevelSwitch(ctx context.Context, switchLoggers []switchlogger.DbSwitchLogger, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[MetadataKey]*MysqlInstanceMetadata{},
	}

	var wg sync.WaitGroup

	for _, inst := range req.MySqlInstData {
		if inst == nil {
			logger.Warn("Mysql switcher get nil instance")
			continue
		}

		wg.Add(1)
		go func(inst *MysqlInstanceMetadata) {
			defer wg.Done()

			instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
			swInst, newErr := m.NewSwitchInstance(inst)
			if newErr != nil {
				logger.Warn("failed to create mysql switcher, inst: %s, errmsg: %s", instKey, newErr)
				rsp.AddFailureInst(instKey, (*dbm.DbInstMetadata)(inst))
				return
			}

			swInst.SetSwitchLogger(switchLoggers)

			logger.Info("start to switch the single mysql instance: %s", instKey)
			if switchSuccess, swErr := SwitchSingleInstance(swInst); !switchSuccess {
				errStr := "nil"
				if swErr != nil {
					errStr = swErr.Error()
				}
				logger.Warn("failed to switch the single mysql instance: %s, errmsg: %s", instKey, errStr)
				rsp.AddFailureInst(instKey, (*dbm.DbInstMetadata)(inst))
				return
			}
			logger.Info("successfully switched the single mysql instance: %s", instKey)
		}(inst)
	}

	wg.Wait()

	if len(rsp.MySqlFailureInsts) == 0 {
		return rsp
	}

	rsp.Err = ErrSwitchPartialSuccess
	return rsp
}

// HostLevelSwitch handles MySQL host switching operations
func (m *Mysql) HostLevelSwitch(ctx context.Context, switchLoggers []switchlogger.DbSwitchLogger, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[MetadataKey]*MysqlInstanceMetadata{},
	}

	ipGroup := make(map[string][]*MysqlInstanceMetadata)
	var wg sync.WaitGroup

	// group instances by ip
	for _, instData := range req.MySqlInstData {
		if instData == nil {
			logger.Warn("Mysql switcher get nil instance")
			continue
		}
		ipGroup[instData.IP] = append(ipGroup[instData.IP], instData)
	}

	// parallelize the processing of the same host
	for ip, instDataList := range ipGroup {
		wg.Add(1)
		go func(ip string, instDataList []*MysqlInstanceMetadata) {
			defer wg.Done()

			sameHostInstances := []SwitchableInstance{}
			dataMap := make(map[MetadataKey]*MysqlInstanceMetadata)

			// create switchable instances for all instances on the same host
			for _, inst := range instDataList {
				instKey := GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
				dataMap[instKey] = inst

				swInst, newErr := m.NewSwitchInstance(inst)
				if newErr == nil {
					swInst.SetSwitchLogger(switchLoggers)
					sameHostInstances = append(sameHostInstances, swInst)
					continue
				}

				logger.Warn("Before switching the host: %s, failed to create mysql switcher, inst: %s, errmsg: %s",
					ip, instKey, newErr)
				rsp.AddFailureInst(instKey, (*dbm.DbInstMetadata)(inst))
				return
			}

			logger.Info("start to switch the host: %s", ip)
			switchSuccess, errMap := SwitchSameHostInstances(sameHostInstances)
			if switchSuccess {
				logger.Info("successfully switched the host: %s", ip)
				return
			}

			logger.Warn("failed to switch the host: %s, errmsg: switch of %d instance(s) failed", ip, len(errMap))
			for instKey := range errMap {
				rsp.AddFailureInst(instKey, (*dbm.DbInstMetadata)(dataMap[instKey]))
			}
		}(ip, instDataList)
	}

	wg.Wait()

	if len(rsp.MySqlFailureInsts) > 0 {
		rsp.Err = ErrSwitchPartialSuccess
	}

	return rsp
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

	switch req.ActionScope {
	case hamodel.ActionScopeTypeCluster:
		rsp.Err = gerrors.Newf(gerrors.Failure, "cluster action scope is not supported")
		return rsp

	case hamodel.ActionScopeTypeHost:
		return m.HostLevelSwitch(ctx, switchLoggers, req)

	default:
		return m.InstanceLevelSwitch(ctx, switchLoggers, req)
	}

}
