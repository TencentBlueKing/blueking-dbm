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
	"sort"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// SwitchExecutor creates switcher requests from failure groups, matches strategies, and triggers switching.
type SwitchExecutor struct {
	hadata    *storage.DbhaData
	dbmSync   *Synchronizer
	switchers map[haprobe.DbType]switcher.Switcher
}

// NewSwitchExecutor creates a SwitchExecutor.
func NewSwitchExecutor(hadata *storage.DbhaData, dbmSync *Synchronizer, switchers map[haprobe.DbType]switcher.Switcher) *SwitchExecutor {
	return &SwitchExecutor{hadata: hadata, dbmSync: dbmSync, switchers: switchers}
}

// CreateRequestWithGroup creates a switcher request from a failure group.
// It queries metadata from DBM for all instances in the group and filters out unavailable ones.
func (e *SwitchExecutor) CreateRequestWithGroup(group *FailureGroup) *switcher.Request {
	ips := group.IPs()
	if len(ips) == 0 {
		logger.Warn("empty IP list in failure group, cloudId: %d, dbType: %s", group.BkCloudID, group.DbType)
		return nil
	}

	metadatas, err := e.dbmSync.QueryMetadataFromDbm(context.Background(), group.BkCloudID, ips)
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

// MatchStrategyForGroup loads strategies for the group's biz, matches by event name/reason and trigger count,
// and returns the highest-priority (smallest Priority value) enabled strategy, or (false, nil) if none match.
func (e *SwitchExecutor) MatchStrategyForGroup(group *FailureGroup) (matched bool, strategy *hamodel.DbSwitchingStrategy) {

	// TODO: only use to test, should remove later
	strategy = &hamodel.DbSwitchingStrategy{
		TriggerEventName:       group.EventName,
		TriggerEventNameReason: group.EventNameReason,
		TriggerCount:           0,
		Priority:               0,
		Scope:                  hamodel.ActionScopeTypeDbInstance,
		Action:                 hamodel.ActionTypeSwitch,
	}

	if len(group.Instances) == 0 {
		return false, nil
	}

	bkBizID := group.Instances[0].BkBizID
	strategies, err := e.hadata.ReadSwitchingStrategyWithBkBizId(bkBizID)
	if err != nil {
		logger.Warn("failed to read switching strategy, bkBizId: %d, errmsg: %s", bkBizID, err)
		return false, nil
	}

	instanceCount := len(group.Instances)
	var candidates []*hamodel.DbSwitchingStrategy
	for _, s := range strategies {
		if s.Status != hamodel.StatusTypeEnabled {
			continue
		}

		if s.TriggerEventName != group.EventName || s.TriggerEventNameReason != group.EventNameReason {
			continue
		}

		threshold := s.TriggerCount
		if threshold <= 0 {
			threshold = 1
		}

		if instanceCount < threshold {
			continue
		}

		candidates = append(candidates, s)
	}

	if len(candidates) == 0 {
		// TODO: only use to test, should remove later
		return true, strategy
		//return false, nil
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].Priority < candidates[j].Priority
	})

	return true, candidates[0]
}

// TriggerSwitching runs the switcher for the given db type and posts success/failure alarms.
func (e *SwitchExecutor) TriggerSwitching(dbType haprobe.DbType, req *switcher.Request) {
	if !config.Cfg.Workflow.EnableSwitching {
		logger.Warn("switching operation is disabled")
		return
	}

	sw, exists := e.switchers[dbType]
	if !exists {
		logger.Warn("unknown database type: %s", dbType)
		return
	}

	rsp := sw.Switch(context.Background(), req)
	if rsp.Err == nil {
		logger.Info("switching success for the database type: %s", dbType)
	}

	// post the success alarm
	for _, inst := range req.GetDbInstMetadata() {
		instKey := switchcore.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)

		if _, exists := rsp.MySqlFailureInsts[instKey]; exists {
			continue
		}

		monitorEvent := &monitor.EventData{
			Name:      string(haprobe.DbEventNameMysqlSwitchSuccessV1),
			Target:    string(instKey),
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		monitorEvent.Content.Content = "switching success"
		monitorEvent.Dimension.BkCloudId = inst.BkCloudID
		monitorEvent.Dimension.IP = inst.IP
		monitorEvent.Dimension.Port = inst.Port
		monitorEvent.Dimension.DbTypeName = dbType
		monitorEvent.Dimension.DbEventName = haprobe.DbEventNameMysqlSwitchSuccessV1

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn("switching success, failed to post the alarm, inst: %s, errmsg: %s", instKey, err)
		}
	}

	// post the failure alarm
	for instKey, inst := range rsp.GetFailureInsts() {
		monitorEvent := &monitor.EventData{
			Name:      string(haprobe.DbEventNameMysqlSwitchFailureV1),
			Target:    string(instKey),
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		monitorEvent.Content.Content = rsp.Err.Error()
		monitorEvent.Dimension.BkCloudId = inst.BkCloudID
		monitorEvent.Dimension.IP = inst.IP
		monitorEvent.Dimension.Port = inst.Port
		monitorEvent.Dimension.DbTypeName = dbType
		monitorEvent.Dimension.DbEventName = haprobe.DbEventNameMysqlSwitchFailureV1

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn("switching failure, failed to post the alarm, inst: %s, errmsg: %s", instKey, err)
		}
	}
}
