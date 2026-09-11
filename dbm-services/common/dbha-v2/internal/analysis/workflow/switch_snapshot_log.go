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

package workflow

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/snapshotlogger"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// NewSwitchingSnapshotData creates snapshot data for switch and notify actions.
func NewSwitchingSnapshotData(
	strategy *hamodel.DbSwitchingStrategy,
	strategies []*hamodel.DbSwitchingStrategy,
	group *FailureGroup,
	req *switcher.Request,
	action hamodel.SnapshotActionType,
	swSnapshotLogger logger.Logger,
) *snapshotlogger.SwitchingSnapshotData {
	if group == nil || swSnapshotLogger == nil {
		return nil
	}

	data := newSnapshotDataBase(group, req, action, swSnapshotLogger)
	data.DbSwitchingSnapshotLog.SetStrategies(strategies)

	strategyID := marshalSnapshotStrategy(data, strategy, swSnapshotLogger)
	marshalSnapshotStrategies(data, strategies, swSnapshotLogger)
	marshalSnapshotFailures(data, group, swSnapshotLogger)
	marshalSnapshotOriginInstances(data, group, swSnapshotLogger)
	fillSnapshotInstances(data, group, req, strategyID, swSnapshotLogger)
	return data
}

func newSnapshotDataBase(
	group *FailureGroup,
	req *switcher.Request,
	action hamodel.SnapshotActionType,
	swSnapshotLogger logger.Logger,
) *snapshotlogger.SwitchingSnapshotData {
	switchID := generateSwitchID()
	actionScope := string(hamodel.ActionScopeTypeNone)
	dbType := string(group.DbType)
	if req != nil {
		switchID = req.SwitchID
		actionScope = string(req.ActionScope)
		dbType = string(req.DbType)
	}

	data := &snapshotlogger.SwitchingSnapshotData{
		DbSwitchingSnapshotLog: &hamodel.DbSwitchingSnapshotLog{
			SwitchID:    switchID,
			BkCloudID:   group.BkCloudID,
			DbType:      dbType,
			ActionScope: actionScope,
			Action:      action,
		},
		SwSnapshotLogger: swSnapshotLogger,
	}
	return data
}

func marshalSnapshotStrategy(
	data *snapshotlogger.SwitchingSnapshotData,
	strategy *hamodel.DbSwitchingStrategy,
	swSnapshotLogger logger.Logger,
) int {
	if strategy == nil {
		return 0
	}

	strategyJSON, err := json.Marshal(strategy)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal strategy for switching snapshot, switchId: %s, errmsg: %s",
			data.DbSwitchingSnapshotLog.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.StrategyJSON = strategyJSON
	}
	return strategy.ID
}

func marshalSnapshotStrategies(
	data *snapshotlogger.SwitchingSnapshotData,
	strategies []*hamodel.DbSwitchingStrategy,
	swSnapshotLogger logger.Logger,
) {
	if strategies == nil {
		return
	}

	strategiesJSON, err := json.Marshal(strategies)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal strategies for switching snapshot, switchId: %s, errmsg: %s",
			data.DbSwitchingSnapshotLog.SwitchID, err)
		return
	}
	data.StdSwitchingSnapshotData.StrategiesJSON = strategiesJSON
}

func marshalSnapshotFailures(
	data *snapshotlogger.SwitchingSnapshotData,
	group *FailureGroup,
	swSnapshotLogger logger.Logger,
) {
	failures := []FailureInstanceInfo{}
	if group.Instances != nil {
		failures = group.Instances
	}

	failureJSON, err := json.Marshal(failures)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal failure instances for switching snapshot, switchId: %s, errmsg: %s",
			data.DbSwitchingSnapshotLog.SwitchID, err)
		return
	}
	data.StdSwitchingSnapshotData.FailureInstancesJSON = failureJSON
	data.DbSwitchingSnapshotLog.BkBizID = group.BkBizID
	if len(group.Instances) > 0 {
		data.DbSwitchingSnapshotLog.Reason = group.Instances[0].EventNameReason.Str().String()
	}
}

func marshalSnapshotOriginInstances(
	data *snapshotlogger.SwitchingSnapshotData,
	group *FailureGroup,
	swSnapshotLogger logger.Logger,
) {
	if group.OriginInstances == nil {
		return
	}

	originJSON, err := json.Marshal(group.OriginInstances)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal origin instances for switching snapshot, switchId: %s, errmsg: %s",
			data.DbSwitchingSnapshotLog.SwitchID, err)
		return
	}
	data.DbSwitchingSnapshotLog.SetOriginInstances(originJSON)
	data.StdSwitchingSnapshotData.OriginInstancesJSON = originJSON
}

func fillSnapshotInstances(
	data *snapshotlogger.SwitchingSnapshotData,
	group *FailureGroup,
	req *switcher.Request,
	strategyID int,
	swSnapshotLogger logger.Logger,
) {
	if req == nil || req.InstData == nil {
		data.DbSwitchingSnapshotLog.SetInstances(buildInstancesListFromFailures(group.Instances, strategyID))
		return
	}

	checkTimeByInst := make(map[string]*FailureInstanceInfo, len(group.Instances))
	for i := range group.Instances {
		inst := &group.Instances[i]
		checkTimeByInst[instanceKey(inst.BkCloudID, inst.IP, inst.Port)] = inst
	}
	data.DbSwitchingSnapshotLog.SetInstances(
		buildInstancesListFromMetadata(req.InstData, checkTimeByInst, strategyID))

	metadataJSON, err := json.Marshal(req.InstData)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal metadata set for switching snapshot, switchId: %s, errmsg: %s",
			data.DbSwitchingSnapshotLog.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.MetadataSetJSON = metadataJSON
	}
}

// SwitchingSnapshotReport is the data structure for switching snapshot reporting.
type SwitchingSnapshotReport struct {
	SnapshotData    *snapshotlogger.SwitchingSnapshotData
	SnapshotLoggers []snapshotlogger.SnapshotLogger
}

// NewSwitchSnapshotLoggers creates the snapshot loggers shared by one failure group.
func NewSwitchSnapshotLoggers(swSnapshotLogger logger.Logger) []snapshotlogger.SnapshotLogger {
	loggers := []snapshotlogger.SnapshotLogger{
		snapshotlogger.NewStdSnapshotHandler(swSnapshotLogger),
	}

	dbSnapshotHdl, err := snapshotlogger.NewDbSnapshotHandlerFromConfig()
	if err != nil {
		logger.Warn("failed to create db snapshot handler, errmsg: %s", err)
		return loggers
	}
	if err = dbSnapshotHdl.Open(); err != nil {
		logger.Warn("failed to open db snapshot handler, errmsg: %s", err)
		dbSnapshotHdl.Close()
		return loggers
	}
	return append(loggers, dbSnapshotHdl)
}

// NewSwitchingSnapshotReport creates a report using shared snapshot loggers.
func NewSwitchingSnapshotReport(
	loggers []snapshotlogger.SnapshotLogger,
	snapshotData *snapshotlogger.SwitchingSnapshotData,
	startTime time.Time,
) *SwitchingSnapshotReport {
	if snapshotData == nil {
		return &SwitchingSnapshotReport{}
	}
	snapshotData.DbSwitchingSnapshotLog.StartTime = &startTime

	return &SwitchingSnapshotReport{
		SnapshotData:    snapshotData,
		SnapshotLoggers: loggers,
	}
}

// ReportBeforeSwitchingSnapshot reports the switching snapshot before switching.
func (s *SwitchingSnapshotReport) ReportBeforeSwitchingSnapshot() {
	if s.SnapshotData == nil {
		return
	}
	if s.SnapshotData.DbSwitchingSnapshotLog == nil {
		return
	}
	s.SnapshotData.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusDoing

	for _, l := range s.SnapshotLoggers {
		if appendErr := l.PreSwitchLog(s.SnapshotData); appendErr != nil {
			logger.Warn("failed to create switching snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.DbSwitchingSnapshotLog.SwitchID, appendErr)
		}
	}
}

// ReportAfterSwitchingSnapshot reports the switching snapshot after switching.
// It updates each instance's new master info from the response, sets the finished time,
// status and result, then delegates to each logger's PostSwitchLog.
func (s *SwitchingSnapshotReport) ReportAfterSwitchingSnapshot(rsp *switcher.Response) {
	if rsp == nil {
		return
	}
	if s.SnapshotData == nil {
		return
	}
	if s.SnapshotData.DbSwitchingSnapshotLog == nil {
		return
	}

	// update new master info for each instance from the switch response
	bkCloudID := s.SnapshotData.DbSwitchingSnapshotLog.BkCloudID
	instances := s.SnapshotData.DbSwitchingSnapshotLog.Instances
	for _, instance := range instances.Data {
		instKey := switchcore.GenerateMetadataKey(bkCloudID, instance.IP, instance.Port)
		if res, has := rsp.GetNewMasterInfo(instKey); has {
			instance.NewMasterIP = res.Host
			instance.NewMasterPort = res.Port
		}
	}

	if instances.Valid {
		// marshal instances
		instancesJSON, err := json.Marshal(instances.Data)
		if err != nil {
			logger.Warn(
				"failed to marshal instances for switching snapshot, switchId: %s, errmsg: %s",
				s.SnapshotData.DbSwitchingSnapshotLog.SwitchID, err)
		}
		s.SnapshotData.InstancesJSON = instancesJSON
	}

	// set finished time, action, status and result based on the switch response
	now := time.Now()
	s.SnapshotData.DbSwitchingSnapshotLog.FinishedTime = &now
	s.SnapshotData.DbSwitchingSnapshotLog.Action = hamodel.SnapshotActionTypePostSwitch
	if rsp.Err != nil {
		s.SnapshotData.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusFailed
		s.SnapshotData.DbSwitchingSnapshotLog.Result = fmt.Sprintf("switching failed: %s", rsp.Err.Error())
	} else {
		s.SnapshotData.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess
		s.SnapshotData.DbSwitchingSnapshotLog.Result = "switching completed successfully"
	}

	for _, l := range s.SnapshotLoggers {
		if appendErr := l.PostSwitchLog(s.SnapshotData); appendErr != nil {
			logger.Warn("failed to create switching snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.DbSwitchingSnapshotLog.SwitchID, appendErr)
		}
	}
}

// ReportNotifySnapshot writes a successful notify snapshot.
func (s *SwitchingSnapshotReport) ReportNotifySnapshot() {
	if s.SnapshotData == nil || s.SnapshotData.DbSwitchingSnapshotLog == nil {
		return
	}

	now := time.Now()
	s.SnapshotData.DbSwitchingSnapshotLog.FinishedTime = &now
	s.SnapshotData.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess
	s.SnapshotData.DbSwitchingSnapshotLog.Result = "notify completed successfully"
	for _, snapshotLogger := range s.SnapshotLoggers {
		if err := snapshotLogger.PreSwitchLog(s.SnapshotData); err != nil {
			logger.Warn("failed to create notify snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.DbSwitchingSnapshotLog.SwitchID, err)
		}
	}
}

// buildInstancesListFromMetadata converts a DbInstMetadata list to a SwitchingSnapshotInstance
// list for database storage. If the instance role is empty, it falls back to the Spider role.
// checkTimeByInst maps each instance to its SSH detection window from the failure group;
// a match extracts the detection times for the corresponding snapshot instance.
func buildInstancesListFromMetadata(
	metaSet []*dbm.DbInstMetadata,
	checkTimeByInst map[string]*FailureInstanceInfo,
	strategyID int,
) []*hamodel.SwitchingSnapshotInstance {
	if metaSet == nil {
		return nil
	}

	instances := make([]*hamodel.SwitchingSnapshotInstance, 0, len(metaSet))
	for _, meta := range metaSet {
		instanceRole := meta.InstanceRole.String()
		if instanceRole == "" && meta.SpiderRole != "" {
			instanceRole = string(meta.SpiderRole)
		}

		var checkStart, checkFinish *time.Time
		var eventName, eventReason string
		if src, ok := checkTimeByInst[instanceKey(meta.BkCloudID, meta.IP, meta.Port)]; ok {
			checkStart = src.CheckStartTime
			checkFinish = src.CheckFinishedTime
			eventName = src.EventName.String()
			eventReason = src.EventNameReason.Str().String()
		}

		instances = append(instances, &hamodel.SwitchingSnapshotInstance{
			ClusterID:         meta.ClusterID,
			ClusterName:       meta.Cluster,
			IP:                meta.IP,
			Port:              meta.Port,
			MachineType:       string(meta.MachineType),
			InstanceRole:      instanceRole,
			StrategyID:        strategyID,
			EventName:         eventName,
			EventNameReason:   eventReason,
			BkIdcID:           meta.BkIdcID,
			CheckStartTime:    checkStart,
			CheckFinishedTime: checkFinish,
		})
	}

	return instances
}

func buildInstancesListFromFailures(
	failures []FailureInstanceInfo,
	strategyID int,
) []*hamodel.SwitchingSnapshotInstance {
	if failures == nil {
		return nil
	}

	instances := make([]*hamodel.SwitchingSnapshotInstance, 0, len(failures))
	for _, failure := range failures {
		instances = append(instances, &hamodel.SwitchingSnapshotInstance{
			ClusterID:         failure.ClusterID,
			ClusterName:       failure.Cluster,
			IP:                failure.IP,
			Port:              failure.Port,
			MachineType:       string(failure.MachineType),
			InstanceRole:      failure.InstanceRole.String(),
			StrategyID:        strategyID,
			EventName:         failure.EventName.String(),
			EventNameReason:   failure.EventNameReason.Str().String(),
			CheckStartTime:    failure.CheckStartTime,
			CheckFinishedTime: failure.CheckFinishedTime,
		})
	}
	return instances
}
