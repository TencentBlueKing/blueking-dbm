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
	"context"
	"errors"
	"fmt"
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/snapshotlogger"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SwitchExecutor creates switcher requests from failure groups, matches strategies, and triggers switching.
type SwitchExecutor struct {
	hadata      *storage.DbhaData
	dbmSync     *Synchronizer
	switchers   map[haprobe.DbType]switcher.Switcher
	myServiceID string
}

// NewSwitchExecutor creates a SwitchExecutor.
func NewSwitchExecutor(hadata *storage.DbhaData, dbmSync *Synchronizer, switchers map[haprobe.DbType]switcher.Switcher, serviceID string) *SwitchExecutor {
	return &SwitchExecutor{hadata: hadata, dbmSync: dbmSync, switchers: switchers, myServiceID: serviceID}
}

// generateDoubleCheckID derives a stable, machine-scoped double-check id from the switch context.
// It is a deterministic function of (switchID, bkCloudID, ip), so it can be called multiple times:
//   - all instances on the same machine within one switch request get the same id;
//   - different machines or different switch requests get different ids.
func generateDoubleCheckID(switchID string, bkCloudID int, ip string) int64 {
	key := fmt.Sprintf("%s|%d|%s", switchID, bkCloudID, ip)
	// Use 63 bits so the hash always fits into a positive int64.
	id := int64(machine.Hash(key, 63))
	// 0 is reserved to mean "uninitialized", so never emit it.
	if id == 0 {
		id = 1
	}
	return id
}

// CreateRequestWithGroup creates a switcher request from a failure group.
// It queries metadata from DBM for all instances in the group and filters out unavailable ones.
func (e *SwitchExecutor) CreateRequestWithGroup(ctx context.Context, group *FailureGroup) *switcher.Request {
	ips := group.IPs()
	if len(ips) == 0 {
		logger.Warn("empty IP list in failure group, cloudId: %d, dbType: %s", group.BkCloudID, group.DbType)
		return nil
	}

	metadatas, err := e.dbmSync.QueryMetadataFromDbm(ctx, group.BkCloudID, ips)
	if err != nil {
		if errors.Is(err, dbm.ErrNoResponse) {
			return nil
		}

		logger.Warn("failed to query metadata from DBM, cloudId: %d, dbType: %s, instances: %d, errmsg: %s",
			group.BkCloudID, group.DbType, len(group.Instances), err)

		return nil
	}

	req := &switcher.Request{DbType: group.DbType}
	skippedCount := 0
	for _, meta := range metadatas {
		if meta.Status == dbm.Unavailable {
			logger.Info("the database instance is unavailable, skipping, inst: %s",
				instanceKey(meta.BkCloudID, meta.IP, meta.Port))
			skippedCount++
			continue
		}

		req.AddDbInstMetadata(meta)
	}

	if skippedCount > 0 {
		logger.Debug("skipped %d unavailable instances, cloudId: %d, dbType: %s",
			skippedCount, group.BkCloudID, group.DbType)
	}

	return req
}

// MatchStrategyForGroup loads biz-level and global strategies, iterates each strategy for matching
// (normal strategies count instances by event name, special strategies invoke registered match functions),
// adds strategies meeting the triggerCount threshold to the candidate list, and returns the highest
// priority strategy after sorting (biz-level first > lower priority value first).
func (e *SwitchExecutor) MatchStrategyForGroup(ctx context.Context, group *FailureGroup) (matched bool, strategy *hamodel.DbSwitchingStrategy) {
	if len(group.Instances) == 0 {
		return false, nil
	}

	bkBizID := group.Instances[0].BkBizID
	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	defer cancel()

	strategies, err := e.hadata.ReadSwitchingStrategyWithBkBizId(qCtx, bkBizID)
	if err != nil {
		logger.Warn("failed to read switching strategy, bkBizId: %d, errmsg: %s", bkBizID, err)
		return false, nil
	}

	var candidates []*hamodel.DbSwitchingStrategy
	for _, s := range strategies {
		threshold := s.TriggerCount
		if threshold <= 0 {
			threshold = 1
		}

		var count int

		// check if this is a special strategy, invoke the corresponding match function
		if matchFunc := GetSpecialMatchFunc(s.TriggerEventName); matchFunc != nil {
			count = matchFunc(group.Instances)
		} else {
			// normal strategy: count instances matching the event name in the group
			count = CountInstancesByEventName(group.Instances, s.TriggerEventName)
		}

		if count >= threshold {
			candidates = append(candidates, s)
		}
	}

	if len(candidates) == 0 {
		return false, nil
	}

	// sort by priority: biz-level first > lower priority value first
	SortCandidates(candidates)

	return true, candidates[0]
}

// excludeUnavailableInstances keeps only the group instances that appear in DBM's query result
// (req.InstData); exclude unavailable instances.
//
// Problem it solves: after a successful switch the failed instance may not recover immediately,
// so its stale failure event can be pushed into the sliding window again. Counting those already-switched
// instances during strategy matching inflates the match count and matches a wrong strategy.
//
// The original group is left untouched so downstream logging and inflight cleanup still see the
// full failure set.
func excludeUnavailableInstances(groupInsts []FailureInstanceInfo, req *switcher.Request) []FailureInstanceInfo {
	if req == nil || len(req.InstData) == 0 {
		return nil
	}

	reqKeys := make(map[string]struct{}, len(req.InstData))
	for _, meta := range req.InstData {
		reqKeys[instanceKey(meta.BkCloudID, meta.IP, meta.Port)] = struct{}{}
	}

	out := make([]FailureInstanceInfo, 0, len(groupInsts))
	for _, inst := range groupInsts {
		if _, ok := reqKeys[instanceKey(inst.BkCloudID, inst.IP, inst.Port)]; ok {
			out = append(out, inst)
		} else {
			logger.Debug("exclude unavailable instance, cloudId: %d, dbType: %s, ip: %s, port: %d",
				inst.BkCloudID, req.DbType, inst.IP, inst.Port)
		}
	}
	return out
}

// TriggerSwitching runs the switcher for the given db type and posts success/failure alarms.
func (e *SwitchExecutor) TriggerSwitching(dbType haprobe.DbType, req *switcher.Request,
	snapshotData *snapshotlogger.SwitchingSnapshotData) {

	if !config.Cfg.Workflow.EnableSwitching {
		logger.Warn("switching operation is disabled")
		return
	}

	sw, exists := e.switchers[dbType]
	if !exists {
		logger.Warn("unknown database type: %s", dbType)
		return
	}

	start := time.Now()
	switchingSnapshotLogger := NewSwitchingSnapshotReport(snapshotData, start)
	defer func() {
		for _, swLogger := range switchingSnapshotLogger.SnapshotLoggers {
			swLogger.Close()
		}
	}()

	// Report before switching snapshot
	switchingSnapshotLogger.ReportBeforeSwitchingSnapshot()

	var rsp *switcher.Response
	safe.Run(func() {
		switchTimeout := config.Cfg.Workflow.SwitchTimeout
		if switchTimeout <= 0 {
			switchTimeout = 10 * time.Minute
		}

		switchCtx, cancel := context.WithTimeout(context.Background(), switchTimeout)
		defer cancel()

		rsp = sw.Switch(switchCtx, req)

		if errors.Is(switchCtx.Err(), context.DeadlineExceeded) {
			logger.Warn("switching timeout, switchTimeout: %s, dbType: %s, switchID: %s", switchTimeout, dbType, req.SwitchID)
		}
	})

	if rsp == nil {
		logger.Error("switch response is nil, possibly due to panic in safe.Run, dbType: %s, switchID: %s",
			dbType, req.SwitchID)
		return
	}

	if rsp.Err == nil {
		logger.Info("switching success for the database type: %s", dbType)
	}

	// Report after switching snapshot
	switchingSnapshotLogger.ReportAfterSwitchingSnapshot(rsp)

	e.reportSwitchingMetrics(start, req, rsp, dbType)
	e.postSuccessAlarms(req, rsp, dbType)
	e.postFailureAlarms(req, rsp, dbType)
}

func (e *SwitchExecutor) reportSwitchingMetrics(start time.Time, req *switcher.Request,
	rsp *switcher.Response, dbType haprobe.DbType) {

	// Report the switching time consuming
	if err := apm.SwitchingTimeConsumingMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelDbType:        dbType.String(),
		haapm.MetricLabelServiceID:   e.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(time.Since(start).Milliseconds())); err != nil {
		logger.Warn("failed to update switching time consuming metric, errmsg: %s", err)
	}

	// Report the switching instance success total and error total
	successCount := float64(len(req.InstData) - rsp.FailureInstCount())
	if err := apm.SwitchingInstanceSuccessTotal.AddWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   e.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, successCount); err != nil {
		logger.Error("failed to update switching instance success total metric, errmsg: %s", err)
	}

	// Report the switching instance error total
	if err := apm.SwitchingInstanceErrorTotal.AddWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   e.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(rsp.FailureInstCount())); err != nil {
		logger.Error("failed to update switching instance error total metric, errmsg: %s", err)
	}
}

func (e *SwitchExecutor) postSuccessAlarms(req *switcher.Request, rsp *switcher.Response,
	dbType haprobe.DbType) {
	failureInsts := rsp.GetFailureInsts()
	successEvent := dbtype.SwitchSuccessEventName(dbType)
	for _, inst := range req.GetDbInstMetadata() {
		instKey := switchcore.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		if _, exists := failureInsts[instKey]; exists {
			continue
		}

		monitorEvent := &monitor.EventData{
			Name:      string(successEvent),
			Target:    string(instKey),
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		monitorEvent.Content.Content = "switching success"
		monitorEvent.Dimension.BkCloudId = inst.BkCloudID
		monitorEvent.Dimension.BkBizId = inst.BkBizID
		monitorEvent.Dimension.SwitchId = req.SwitchID
		monitorEvent.Dimension.IP = inst.IP
		monitorEvent.Dimension.Port = inst.Port
		monitorEvent.Dimension.DbTypeName = dbType
		monitorEvent.Dimension.DbEventName = successEvent

		// Populate the v1 dimensions to support self-healing tickets.
		monitorEvent.Dimension.SwitchInfoServerIpV1 = inst.IP
		monitorEvent.Dimension.SwitchInfoServerPortV1 = inst.Port
		monitorEvent.Dimension.SwitchInfoInstanceRoleV1 = string(inst.InstanceRole)
		monitorEvent.Dimension.SwitchInfoBkBizIdV1 = strconv.Itoa(inst.BkBizID)
		monitorEvent.Dimension.SwitchInfoClusterDomainV1 = inst.Cluster
		monitorEvent.Dimension.SwitchInfoMachineTypeV1 = string(inst.MachineType)
		monitorEvent.Dimension.SwitchInfoIdcV1 = strconv.Itoa(inst.BkIdcCityID)
		monitorEvent.Dimension.SwitchInfoStatusV1 = string(inst.Status)
		monitorEvent.Dimension.SwitchInfoCheckIdV1 = generateDoubleCheckID(req.SwitchID, inst.BkCloudID, inst.IP)

		if newMaster, ok := rsp.GetNewMasterInfo(instKey); ok {
			monitorEvent.Dimension.SwitchInfoNewMasterHost = newMaster.Host
			monitorEvent.Dimension.SwitchInfoNewMasterPort = newMaster.Port
			monitorEvent.Dimension.SwitchInfoNewMasterBinlogFile = newMaster.BinlogFile
			monitorEvent.Dimension.SwitchInfoNewMasterBinlogPos = newMaster.BinlogPos
		}

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn(
				"switching success, failed to post the alarm, inst: %s, errmsg: %s",
				instKey,
				err,
			)
		}
	}
}

func (e *SwitchExecutor) postFailureAlarms(req *switcher.Request, rsp *switcher.Response, dbType haprobe.DbType) {
	failureEvent := dbtype.SwitchFailureEventName(dbType)
	for instKey, inst := range rsp.GetFailureInsts() {
		monitorEvent := &monitor.EventData{
			Name:      string(failureEvent),
			Target:    string(instKey),
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		monitorEvent.Content.Content = rsp.Err.Error()
		monitorEvent.Dimension.BkCloudId = inst.BkCloudID
		monitorEvent.Dimension.BkBizId = inst.BkBizID
		monitorEvent.Dimension.SwitchId = req.SwitchID
		monitorEvent.Dimension.IP = inst.IP
		monitorEvent.Dimension.Port = inst.Port
		monitorEvent.Dimension.DbTypeName = dbType
		monitorEvent.Dimension.DbEventName = failureEvent

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn("switching failure, failed to post the alarm, inst: %s, errmsg: %s", instKey, err)
		}
	}
}
