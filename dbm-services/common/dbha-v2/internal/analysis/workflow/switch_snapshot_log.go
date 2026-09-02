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

// NewSwitchingSnapshotData creates a new SwitchingSnapshotData instance.
// strategy is the matched strategy (may be nil for unmatched instances); strategies is the full
// strategy list queried from DB for tracing; req is the switcher request (nil for notify);
// action identifies the snapshot action (pre-switch / post-switch / notify).
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

// newSnapshotDataBase builds the base snapshot data with the switch/notify common fields.
func newSnapshotDataBase(
	group *FailureGroup,
	req *switcher.Request,
	action hamodel.SnapshotActionType,
	swSnapshotLogger logger.Logger,
) *snapshotlogger.SwitchingSnapshotData {
	switchID := ""
	actionScope := string(hamodel.ActionScopeTypeNone)
	dbType := string(group.DbType)
	if req != nil {
		switchID = req.SwitchID
		actionScope = string(req.ActionScope)
		dbType = string(req.DbType)
	} else {
		// notify: generate the switch id.
		switchID = generateSwitchID()
	}

	return &snapshotlogger.SwitchingSnapshotData{
		DbSwitchingSnapshotLog: &hamodel.DbSwitchingSnapshotLog{
			SwitchID:    switchID,
			BkCloudID:   group.BkCloudID,
			DbType:      dbType,
			ActionScope: actionScope,
			Action:      action,
		},
		SwSnapshotLogger: swSnapshotLogger,
	}
}

// marshalSnapshotStrategy marshals the matched strategy and returns its ID (0 if nil).
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

// marshalSnapshotStrategies marshals the full queried strategy list for tracing.
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
	} else {
		data.StdSwitchingSnapshotData.StrategiesJSON = strategiesJSON
	}
}

// marshalSnapshotFailures marshals the failure instances and fills BkBizID/Reason from the first one.
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

// marshalSnapshotOriginInstances marshals the original (pre-match) failure group instances and
// fills both the DB field (origin_instances) and the std log field (origin_instances), so each
// switch/notify record can reproduce the whole original failure scope.
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

// fillSnapshotInstances builds the instance list: switch uses DBM metadata (and marshals the
// metadata set), notify uses the failure instances directly.
func fillSnapshotInstances(
	data *snapshotlogger.SwitchingSnapshotData,
	group *FailureGroup,
	req *switcher.Request,
	strategyID int,
	swSnapshotLogger logger.Logger,
) {
	if req != nil && req.MySqlInstData != nil {
		// build a lookup of instance detection times (from the SSH double-check) keyed by instance
		checkTimeByInst := make(map[string]*FailureInstanceInfo, len(group.Instances))
		for i := range group.Instances {
			inst := &group.Instances[i]
			checkTimeByInst[instanceKey(inst.BkCloudID, inst.IP, inst.Port)] = inst
		}

		instances := buildInstancesListFromMetadata(req.MySqlInstData, checkTimeByInst, strategyID)
		data.DbSwitchingSnapshotLog.SetInstances(instances)

		metadataJSON, err := json.Marshal(req.MySqlInstData)
		if err != nil {
			swSnapshotLogger.Warn(
				"failed to marshal metadata set for switching snapshot, switchId: %s, errmsg: %s",
				data.DbSwitchingSnapshotLog.SwitchID, err)
		} else {
			data.StdSwitchingSnapshotData.MetadataSetJSON = metadataJSON
		}
		return
	}

	// notify: build instances from failure info directly (no DBM metadata)
	instances := buildInstancesListFromFailures(group.Instances, strategyID)
	data.DbSwitchingSnapshotLog.SetInstances(instances)
}

// SwitchingSnapshotReport is the data structure for switching snapshot reporting.
type SwitchingSnapshotReport struct {
	SnapshotData    *snapshotlogger.SwitchingSnapshotData
	SnapshotLoggers []snapshotlogger.SnapshotLogger
}

// NewSwitchSnapshotLoggers creates the snapshot loggers shared by all the tasks of one failure group.
func NewSwitchSnapshotLoggers(swSnapshotLogger logger.Logger) []snapshotlogger.SnapshotLogger {
	loggers := []snapshotlogger.SnapshotLogger{
		snapshotlogger.NewStdSnapshotHandler(swSnapshotLogger),
	}

	dbSnapshotHdl, dbSnapshotErr := snapshotlogger.NewDbSnapshotHandlerFromConfig()
	if dbSnapshotErr != nil {
		logger.Warn("failed to create db snapshot handler, errmsg: %s", dbSnapshotErr)
		return loggers
	}

	if openErr := dbSnapshotHdl.Open(); openErr != nil {
		logger.Warn("failed to open db snapshot handler, errmsg: %s", openErr)
		dbSnapshotHdl.Close()
		return loggers
	}

	loggers = append(loggers, dbSnapshotHdl)
	return loggers
}

// NewSwitchingSnapshotReport creates a new SwitchingSnapshotReport instance for one snapshot.
func NewSwitchingSnapshotReport(loggers []snapshotlogger.SnapshotLogger,
	snapshotData *snapshotlogger.SwitchingSnapshotData, startTime time.Time) *SwitchingSnapshotReport {
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
		if res, has := rsp.GetMySqlNewMasterInfo(instKey); has {
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

// ReportNotifySnapshot writes a notify snapshot record (single insert, success status).
func (s *SwitchingSnapshotReport) ReportNotifySnapshot() {
	if s.SnapshotData == nil {
		return
	}
	if s.SnapshotData.DbSwitchingSnapshotLog == nil {
		return
	}

	now := time.Now()
	s.SnapshotData.DbSwitchingSnapshotLog.FinishedTime = &now
	s.SnapshotData.DbSwitchingSnapshotLog.Status = hamodel.DbSwitchingSnapshotLogStatusSuccess
	s.SnapshotData.DbSwitchingSnapshotLog.Result = "notify completed successfully"

	for _, l := range s.SnapshotLoggers {
		if appendErr := l.PreSwitchLog(s.SnapshotData); appendErr != nil {
			logger.Warn("failed to create notify snapshot record, switchId: %s, errmsg: %s",
				s.SnapshotData.DbSwitchingSnapshotLog.SwitchID, appendErr)
		}
	}
}

// buildInstancesListFromMetadata converts a DbInstMetadata list to a SwitchingSnapshotInstance
// list for database storage. If the instance role is empty, it falls back to the Spider role.
// checkTimeByInst maps each instance to its failure info from the failure group;
// a match extracts the detection times, event name and event reason for the snapshot instance.
// strategyID is the strategy bound to all instances in the group.
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

// buildInstancesListFromFailures converts failure instances to a SwitchingSnapshotInstance
// list for notify snapshots (no DBM metadata query involved).
// strategyID is the strategy bound to all instances in the group (0 for unmatched).
func buildInstancesListFromFailures(
	failures []FailureInstanceInfo,
	strategyID int,
) []*hamodel.SwitchingSnapshotInstance {
	if failures == nil {
		return nil
	}

	instances := make([]*hamodel.SwitchingSnapshotInstance, 0, len(failures))
	for _, f := range failures {
		instances = append(instances, &hamodel.SwitchingSnapshotInstance{
			ClusterID:         f.ClusterID,
			ClusterName:       f.Cluster,
			IP:                f.IP,
			Port:              f.Port,
			MachineType:       string(f.MachineType),
			InstanceRole:      f.InstanceRole.String(),
			StrategyID:        strategyID,
			EventName:         f.EventName.String(),
			EventNameReason:   f.EventNameReason.Str().String(),
			CheckStartTime:    f.CheckStartTime,
			CheckFinishedTime: f.CheckFinishedTime,
		})
	}

	return instances
}
