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
func NewSwitchingSnapshotData(
	strategy *hamodel.DbSwitchingStrategy,
	group *FailureGroup,
	req *switcher.Request,
	swSnapshotLogger logger.Logger,
) *snapshotlogger.SwitchingSnapshotData {
	if strategy == nil || group == nil || req == nil || swSnapshotLogger == nil {
		return nil
	}

	data := &snapshotlogger.SwitchingSnapshotData{
		DbSwitchingSnapshotLog: &hamodel.DbSwitchingSnapshotLog{
			SwitchID:    req.SwitchID,
			BkCloudID:   group.BkCloudID,
			DbType:      string(req.DbType),
			ActionScope: string(req.ActionScope),
		},
		SwSnapshotLogger: swSnapshotLogger,
	}

	// marshal strategy
	strategyJSON, err := json.Marshal(strategy)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal strategy for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.StrategyJSON = strategyJSON
	}

	// marshal failure instances
	failures := []FailureInstanceInfo{}
	if group.Instances != nil {
		failures = group.Instances
	}

	failureJSON, err := json.Marshal(failures)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal failure instances for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.FailureInstancesJSON = failureJSON

		if len(group.Instances) > 0 {
			data.DbSwitchingSnapshotLog.BkBizID = group.Instances[0].BkBizID
			data.DbSwitchingSnapshotLog.Reason = group.Instances[0].EventNameReason.Str().String()
		}
	}

	// marshal metadata set
	metaSet := []*dbm.DbInstMetadata{}
	if req.InstData != nil {
		metaSet = req.InstData
	}

	// build a lookup of instance detection times (from the SSH double-check) keyed by instance
	checkTimeByInst := make(map[string]*FailureInstanceInfo, len(group.Instances))
	for i := range group.Instances {
		inst := &group.Instances[i]
		checkTimeByInst[instanceKey(inst.BkCloudID, inst.IP, inst.Port)] = inst
	}

	// set instances on the DB log record for persistence
	instances := buildInstancesListFromMetadata(metaSet, checkTimeByInst)
	data.DbSwitchingSnapshotLog.SetInstances(instances)

	metadataJSON, err := json.Marshal(metaSet)
	if err != nil {
		swSnapshotLogger.Warn(
			"failed to marshal metadata set for switching snapshot, switchId: %s, errmsg: %s",
			req.SwitchID, err)
	} else {
		data.StdSwitchingSnapshotData.MetadataSetJSON = metadataJSON
	}

	return data
}

// SwitchingSnapshotReport is the data structure for switching snapshot reporting.
type SwitchingSnapshotReport struct {
	SnapshotData    *snapshotlogger.SwitchingSnapshotData
	SnapshotLoggers []snapshotlogger.SnapshotLogger
}

// NewSwitchingSnapshotReport creates a new SwitchingSnapshotReport instance.
// It initializes the DB snapshot handler and the file (stdout) snapshot handler.
func NewSwitchingSnapshotReport(snapshotData *snapshotlogger.SwitchingSnapshotData, startTime time.Time) *SwitchingSnapshotReport {
	if snapshotData == nil {
		return &SwitchingSnapshotReport{}
	}
	snapshotData.DbSwitchingSnapshotLog.StartTime = &startTime

	snapshotLoggers := []snapshotlogger.SnapshotLogger{}

	// initialize the database snapshot handler
	dbSnapshotHdl, dbSnapshotErr := snapshotlogger.NewDbSnapshotHandlerFromConfig()
	if dbSnapshotErr != nil {
		logger.Warn("failed to create db snapshot handler, switchId: %s, errmsg: %s",
			snapshotData.DbSwitchingSnapshotLog.SwitchID, dbSnapshotErr)
	} else {
		if openErr := dbSnapshotHdl.Open(); openErr != nil {
			logger.Warn("failed to open db snapshot handler, switchId: %s, errmsg: %s",
				snapshotData.DbSwitchingSnapshotLog.SwitchID, openErr)
			dbSnapshotHdl.Close()
		} else {
			snapshotLoggers = append(snapshotLoggers, dbSnapshotHdl)
		}
	}

	// initialize the file (stdout) snapshot handler
	swSnapshotLogger := snapshotlogger.NewStdSnapshotHandler(snapshotData.SwSnapshotLogger)
	snapshotLoggers = append(snapshotLoggers, swSnapshotLogger)

	return &SwitchingSnapshotReport{
		SnapshotData:    snapshotData,
		SnapshotLoggers: snapshotLoggers,
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

	// set finished time, status and result based on the switch response
	now := time.Now()
	s.SnapshotData.DbSwitchingSnapshotLog.FinishedTime = &now
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

// buildInstancesListFromMetadata converts a DbInstMetadata list to a SwitchingSnapshotInstance
// list for database storage. If the instance role is empty, it falls back to the Spider role.
// checkTimeByInst maps each instance to its SSH detection window from the failure group;
// a match extracts the detection times for the corresponding snapshot instance.
func buildInstancesListFromMetadata(
	metaSet []*dbm.DbInstMetadata,
	checkTimeByInst map[string]*FailureInstanceInfo,
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
		if src, ok := checkTimeByInst[instanceKey(meta.BkCloudID, meta.IP, meta.Port)]; ok {
			checkStart = src.CheckStartTime
			checkFinish = src.CheckFinishedTime
		}

		instances = append(instances, &hamodel.SwitchingSnapshotInstance{
			ClusterID:         meta.ClusterID,
			ClusterName:       meta.Cluster,
			IP:                meta.IP,
			Port:              meta.Port,
			MachineType:       string(meta.MachineType),
			InstanceRole:      instanceRole,
			BkIdcID:           meta.BkIdcID,
			CheckStartTime:    checkStart,
			CheckFinishedTime: checkFinish,
		})
	}

	return instances
}
