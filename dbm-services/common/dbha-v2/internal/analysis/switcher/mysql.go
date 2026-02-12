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
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/mysql"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ Switcher = (*Mysql)(nil)

// Mysql implements the Switcher interface for MySQL database instances
type Mysql struct {
}

// DbTypeName returns the MySQL database type identifier
func (m *Mysql) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeMySql
}

// NewSwitchInstance creates a MySQL switch instance according to the provided metadata
func (m *Mysql) NewSwitchInstance(metadata *dbm.DbInstMetadata, switchID string, actionScope hamodel.ActionScopeType) (
	switchableInstance switchcore.SwitchableInstance, retErr error) {

	switch metadata.ClusterType {
	case haprobe.DbmMetadataClusterTypeTendbha:
		switchableInstance, retErr = mysql.NewMySQLSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypeTendbCluster:
		switchableInstance, retErr = mysql.NewTendbClusterSwitchInstance(metadata)

	default:
		return nil, gerrors.Newf(gerrors.Failure, "unsupported cluster type: %s", metadata.ClusterType)
	}

	if retErr != nil {
		return nil, retErr
	}

	switchableInstance.SetSwitchID(switchID)
	switchableInstance.SetActionScope(actionScope)

	return switchableInstance, nil
}

// NewSwitchInstancesOnSameHost creates switchable instances for all instances on the same host
func (m *Mysql) NewSwitchInstancesOnSameHost(instDataMap switchcore.InstMetadataMap, switchID string,
	actionScope hamodel.ActionScopeType) (map[switchcore.MetadataKey]switchcore.SwitchableInstance, error) {
	swInstMap := map[switchcore.MetadataKey]switchcore.SwitchableInstance{}

	for instKey, inst := range instDataMap {
		swInst, newErr := m.NewSwitchInstance(inst, switchID, actionScope)
		if newErr != nil {
			return nil, gerrors.Newf(gerrors.Failure, "failed to create mysql switcher, inst: %s, errmsg: %s",
				instKey, newErr.Error())
		}
		swInstMap[instKey] = swInst
	}

	return swInstMap, nil
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
		MySqlFailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}

	seenInsts := make(map[switchcore.MetadataKey]struct{})
	var wg sync.WaitGroup

	for _, inst := range req.MySqlInstData {
		if inst == nil {
			logger.Warn("Mysql switcher get nil instance")
			continue
		}

		instKey := switchcore.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		if _, exists := seenInsts[instKey]; exists {
			logger.Warn("Mysql switcher got duplicate instance in request, inst: %s", instKey)
			continue // skip duplicate instance
		}
		seenInsts[instKey] = struct{}{}

		wg.Add(1)
		go func(inst *dbm.DbInstMetadata, instKey switchcore.MetadataKey) {
			defer wg.Done()

			swReporter := NewSwitchReporter(switchLoggers, switchcore.InstMetadataMap{instKey: inst},
				req.SwitchID, req.ActionScope)
			swReporter.ReportSwitchLogf(switchlogger.SwitchInfo, "start to switch the single mysql instance")

			swInst, newErr := m.NewSwitchInstance(inst, req.SwitchID, req.ActionScope)
			if newErr != nil {
				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "failed to create mysql switcher, errmsg: %s", newErr.Error())
				rsp.AddFailureInst(instKey, inst)
				return
			}

			swInst.SetSwitchLogger(switchLoggers)

			if switchSuccess, swErr := switchcore.SwitchSingleInstance(swInst); !switchSuccess {
				errStr := "nil"
				if swErr != nil {
					errStr = swErr.Error()
				}

				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "failed to switch the single mysql instance, errmsg: %s",
					errStr)
				rsp.AddFailureInst(instKey, inst)
				return
			}

			swReporter.ReportSwitchLogf(switchlogger.SwitchSuccess, "successfully switched the single mysql instance: %s",
				instKey)
		}(inst, instKey)
	}

	wg.Wait()

	if len(rsp.MySqlFailureInsts) == 0 {
		return rsp
	}

	rsp.Err = ErrSwitchPartialSuccess
	return rsp
}

// buildIpGroup builds a map of IP to instance metadata
func (m *Mysql) buildIpGroup(req *Request) map[switchcore.HostKey]switchcore.InstMetadataMap {
	ipGroup := make(map[switchcore.HostKey]switchcore.InstMetadataMap)
	for _, instData := range req.MySqlInstData {
		if instData == nil {
			logger.Warn("Mysql switcher get nil instance")
			continue
		}

		host := switchcore.GenerateHostKey(instData.BkCloudID, instData.IP)
		instKey := switchcore.GenerateMetadataKey(instData.BkCloudID, instData.IP, instData.Port)
		insts, ok := ipGroup[host]
		if !ok {
			insts = switchcore.InstMetadataMap{}
			ipGroup[host] = insts
		}

		if _, exists := insts[instKey]; exists {
			logger.Warn("Mysql switcher got duplicate instance on same host, host: %s, inst: %s", host.String(), instKey)
			continue
		}
		insts[instKey] = instData
	}

	return ipGroup
}

// checkHostInstanceCompleteness checks if there are extra or missing instances on the same host.
func (m *Mysql) checkHostInstanceCompleteness(ctx context.Context, host switchcore.HostKey,
	instDataMap switchcore.InstMetadataMap) error {

	extraInsts := []string{}
	missingInsts := []string{}

	dbmClient := &dbm.Client{}
	metas, err := dbmClient.QueryMetadataFromDbm(ctx, host.BkCloudID, []string{host.IP})
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to query metadata from dbm, host: %s, errmsg: %s",
			host.String(), err.Error())
	}

	expected := make(map[switchcore.MetadataKey]struct{})
	for _, meta := range metas {
		instKey := switchcore.GenerateMetadataKey(meta.BkCloudID, meta.IP, meta.Port)
		expected[instKey] = struct{}{}
	}

	actual := make(map[switchcore.MetadataKey]struct{})
	for instKey := range instDataMap {
		actual[instKey] = struct{}{}
	}

	for instKey := range actual {
		if _, exists := expected[instKey]; !exists {
			extraInsts = append(extraInsts, string(instKey))
		}
	}

	for instKey := range expected {
		if _, exists := actual[instKey]; !exists {
			missingInsts = append(missingInsts, string(instKey))
		}
	}

	if (len(extraInsts) > 0) || (len(missingInsts) > 0) {
		extraInstsStr := strings.Join(extraInsts, ", ")
		missingInstsStr := strings.Join(missingInsts, ", ")
		return gerrors.Newf(gerrors.Failure, "host instance mismatches were found, host: %s, "+
			"extraInsts: %s, missingInsts: %s", host.String(), extraInstsStr, missingInstsStr)
	}

	return nil
}

// HostLevelSwitch handles MySQL host switching operations
func (m *Mysql) HostLevelSwitch(ctx context.Context, switchLoggers []switchlogger.DbSwitchLogger, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}

	addAllInstsAsFailure := func(instDataMap switchcore.InstMetadataMap) {
		for instKey, inst := range instDataMap {
			rsp.AddFailureInst(instKey, inst)
		}
	}

	ipGroup := m.buildIpGroup(req)
	var wg sync.WaitGroup

	// parallelize the processing of the same host
	for host, instDataMap := range ipGroup {
		wg.Add(1)

		go func(host switchcore.HostKey, instDataMap switchcore.InstMetadataMap) {
			defer wg.Done()

			swReporter := NewSwitchReporter(switchLoggers, instDataMap, req.SwitchID, req.ActionScope)
			swReporter.ReportSwitchLogf(switchlogger.SwitchInfo, "start to switch all instances on the current host, "+
				"instances: [%s]", strings.Join(switchcore.ExtractMetadataKeys(instDataMap), ", "))

			if err := m.checkHostInstanceCompleteness(ctx, host, instDataMap); err != nil {
				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "while checking host instance completeness, %s", err.Error())
				addAllInstsAsFailure(instDataMap)
				return
			}

			swInstMap, newErr := m.NewSwitchInstancesOnSameHost(instDataMap, req.SwitchID, req.ActionScope)
			if newErr != nil {
				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "failed to create all mysql switchers on the same host, "+
					"errmsg: %s", newErr.Error())
				addAllInstsAsFailure(instDataMap)
				return
			}

			for _, swInst := range swInstMap {
				swInst.SetSwitchLogger(switchLoggers)
			}

			switchSuccess, errMap := switchcore.SwitchSameHostInstances(swInstMap)
			if switchSuccess {
				swReporter.ReportSwitchLogf(switchlogger.SwitchSuccess, "successfully switched all instances on the current host")
				return
			}

			failedInstStr := "[" + strings.Join(switchcore.ExtractMetadataKeys(errMap), ", ") + "]"

			for instKey, swInst := range swInstMap {
				if err, exists := errMap[instKey]; exists {
					swInst.ReportLogf(switchlogger.SwitchFail, "failed to switch all instances on the same host, "+
						"failed instances: %s, errmsg: %s", failedInstStr, err.Error())
					rsp.AddFailureInst(instKey, instDataMap[instKey])
					continue
				}

				swInst.ReportLogf(switchlogger.SwitchSuccess, "Only some instances on this host were switched successfully.")
			}
		}(host, instDataMap)
	}

	wg.Wait()

	if len(rsp.MySqlFailureInsts) > 0 {
		rsp.Err = ErrSwitchPartialSuccess
	}

	return rsp
}

// Switch handles MySQL switching operations on different levels
func (m *Mysql) Switch(ctx context.Context, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}

	if req == nil {
		rsp.Err = gerrors.Newf(gerrors.Failure, "Mysql switcher get nil switch request")
		logger.Error("%s", rsp.Err.Error())
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

	case hamodel.ActionScopeTypeDbInstance:
		return m.InstanceLevelSwitch(ctx, switchLoggers, req)

	default:
		rsp.Err = gerrors.Newf(gerrors.Failure, "Mysql switcher got unknown action scope: %s", req.ActionScope)
		logger.Error("%s", rsp.Err.Error())

		for _, instData := range req.GetDbInstMetadata() {
			instKey := switchcore.GenerateMetadataKey(instData.BkCloudID, instData.IP, instData.Port)
			rsp.AddFailureInst(instKey, instData)
		}

		return rsp
	}

}
