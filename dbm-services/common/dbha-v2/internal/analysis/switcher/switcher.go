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
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/mysql"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	ErrSwitchPartialSuccess = gerrors.Newf(gerrors.Failure, "the switching achieved partial success")
)

// Request contains all data needed for database switching operation
type Request struct {
	SwitchID    string
	ActionScope hamodel.ActionScopeType
	DbType      haprobe.DbType
	InstData    []*dbm.DbInstMetadata
}

// AddDbInstMetadata TODO: Need to adapt to different types of DB instance data
func (req *Request) AddDbInstMetadata(metadata *dbm.DbInstMetadata) {
	req.InstData = append(req.InstData, metadata)
}

// HasDbInstMetadata checks if there is any database instance data
func (req *Request) HasDbInstMetadata() bool {
	return len(req.InstData) > 0
}

// GetDbInstMetadata gets all database instance data
// TODO: Need to adapt to different types of DB instance data
func (req *Request) GetDbInstMetadata() []*dbm.DbInstMetadata {
	return req.InstData
}

// Response contains the result of switching operation
type Response struct {
	FailureInsts       map[switchcore.MetadataKey]*dbm.DbInstMetadata
	MySqlNewMasterInfo map[switchcore.MetadataKey]*mysql.MySqlNewMasterInfo
	Err                error
	mu                 sync.Mutex
}

// GetFailureInsts returns a copy of failed instances under rsp.mu.
func (rsp *Response) GetFailureInsts() map[switchcore.MetadataKey]*dbm.DbInstMetadata {
	if rsp == nil {
		return nil
	}

	rsp.mu.Lock()
	defer rsp.mu.Unlock()

	if rsp.FailureInsts == nil {
		return nil
	}

	insts := make(map[switchcore.MetadataKey]*dbm.DbInstMetadata, len(rsp.FailureInsts))
	for k, v := range rsp.FailureInsts {
		insts[k] = v
	}
	return insts
}

// FailureInstCount returns the number of failed instances under rsp.mu.
func (rsp *Response) FailureInstCount() int {
	if rsp == nil {
		return 0
	}
	rsp.mu.Lock()
	defer rsp.mu.Unlock()
	return len(rsp.FailureInsts)
}

// AddFailureInst appends a failure instance in a concurrency-safe way.
func (rsp *Response) AddFailureInst(instKey switchcore.MetadataKey, inst *dbm.DbInstMetadata) {
	if rsp == nil {
		return
	}
	if inst == nil {
		return
	}

	rsp.mu.Lock()
	defer rsp.mu.Unlock()

	if rsp.FailureInsts == nil {
		rsp.FailureInsts = map[switchcore.MetadataKey]*dbm.DbInstMetadata{}
	}
	rsp.FailureInsts[instKey] = inst
}

// AddNewMasterInfo records the new master info in a concurrency-safe way.
func (rsp *Response) AddNewMasterInfo(instKey switchcore.MetadataKey, info *mysql.MySqlNewMasterInfo) {
	if rsp == nil {
		return
	}
	if info == nil {
		return
	}

	rsp.mu.Lock()
	defer rsp.mu.Unlock()

	if rsp.MySqlNewMasterInfo == nil {
		rsp.MySqlNewMasterInfo = map[switchcore.MetadataKey]*mysql.MySqlNewMasterInfo{}
	}
	rsp.MySqlNewMasterInfo[instKey] = info
}

// recordInstanceNewMaster records the new master info of a successfully switched instance, if any.
func (rsp *Response) recordInstanceNewMaster(instKey switchcore.MetadataKey, swInst switchcore.SwitchableInstance) {
	provider, ok := swInst.(mysql.InstanceNewMasterProvider)
	if !ok {
		return
	}

	if info, has := provider.GetNewMasterInfo(); has {
		rsp.AddNewMasterInfo(instKey, info)
	}
}

// recordClusterNewMasters records the new master info of a successfully switched cluster, if any.
func (rsp *Response) recordClusterNewMasters(swCluster switchcore.SwitchableCluster) {
	provider, ok := swCluster.(mysql.ClusterNewMasterProvider)
	if !ok {
		return
	}

	for instKey, info := range provider.GetNewMasterInfos() {
		rsp.AddNewMasterInfo(instKey, info)
	}
}

// GetMySqlNewMasterInfo returns the new master info for the given mysql instance, if any.
func (rsp *Response) GetMySqlNewMasterInfo(instKey switchcore.MetadataKey) (*mysql.MySqlNewMasterInfo, bool) {
	if rsp == nil || rsp.MySqlNewMasterInfo == nil {
		return nil, false
	}

	info, ok := rsp.MySqlNewMasterInfo[instKey]
	return info, ok
}

// Switcher defines the interface for database switching implementations
type Switcher interface {
	DbTypeName() haprobe.DbType
	Switch(ctx context.Context, req *Request) *Response
}

// SwitchReporter is the reporter for database switching operations
type SwitchReporter struct {
	SwitchLoggers []switchlogger.DbSwitchLogger
	InstDataMap   switchcore.InstMetadataMap
	SwitchID      string
	ActionScope   hamodel.ActionScopeType
}

// NewSwitchReporter creates a new switch reporter
func NewSwitchReporter(switchLoggers []switchlogger.DbSwitchLogger, instDataMap switchcore.InstMetadataMap,
	switchID string, actionScope hamodel.ActionScopeType) *SwitchReporter {

	return &SwitchReporter{
		SwitchLoggers: switchLoggers,
		InstDataMap:   instDataMap,
		SwitchID:      switchID,
		ActionScope:   actionScope,
	}
}

// ReportSwitchLog records switching operation logs with specified level
func (sr *SwitchReporter) ReportSwitchLog(level switchlogger.SwitchLogLevel, message string) bool {
	// use default logger if no logger is provided
	if len(sr.SwitchLoggers) == 0 {
		sr.SwitchLoggers = []switchlogger.DbSwitchLogger{switchlogger.NewLogToStdHandler()}
		logger.Info("no switch loggers provided for switch reporter, using default logger for switch log, "+
			"switchID: %s, actionScope: %s", sr.SwitchID, sr.ActionScope)
	}

	logTime := time.Now()
	for _, inst := range sr.InstDataMap {
		logRecord := hamodel.DbSwitchingLog{
			SwitchID:    sr.SwitchID,
			ActionScope: string(sr.ActionScope),
			BkBizID:     inst.BkBizID,
			BkCloudID:   inst.BkCloudID,
			DbIP:        inst.IP,
			DbPort:      inst.Port,
			ClusterID:   inst.ClusterID,
			ClusterName: inst.Cluster,
			DbTypeName:  string(inst.MachineType),
			Level:       string(level),
			Content:     message,
			CreatedTime: logTime,
		}

		for _, swlogger := range sr.SwitchLoggers {
			if logErr := swlogger.Append(&logRecord); logErr != nil {
				logger.Warn("failed to append switch log record, inst: %d:%s:%d, err: %s",
					inst.BkCloudID, inst.IP, inst.Port, logErr.Error())
			}
		}
	}

	return true
}

// ReportSwitchLogf records formatted switching operation logs
func (sr *SwitchReporter) ReportSwitchLogf(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
	return sr.ReportSwitchLog(level, fmt.Sprintf(format, args...))
}
