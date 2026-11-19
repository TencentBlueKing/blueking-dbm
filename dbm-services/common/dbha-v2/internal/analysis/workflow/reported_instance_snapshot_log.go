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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const defaultReportedInstanceTTL = 10 * time.Minute

// reportLogKind identifies which kind of snapshot log recorded an instance.
type reportLogKind uint8

const (
	// reportLogSkippedSwitch matches skipped-switch records (pre-switch + failed).
	reportLogSkippedSwitch reportLogKind = iota
	// reportLogNotifyOnly matches notify-only records (notify + success).
	reportLogNotifyOnly
)

// reportedSnapshotInstance describes an instance already written to a snapshot log.
type reportedSnapshotInstance struct {
	EventName haprobe.DbEventName
	StartTime time.Time
	TTL       time.Duration
}

// matchReportedEvent reports whether a snapshot log record matches the current event.
func matchReportedEvent(record reportedSnapshotInstance, event haprobe.DbEventName) bool {
	return record.EventName == event
}

// reportedInstanceTTL returns the configured cache TTL, with a safe fallback.
func reportedInstanceTTL() time.Duration {
	if config.Cfg.Workflow.ReportedInstanceTTL > 0 {
		return config.Cfg.Workflow.ReportedInstanceTTL
	}
	logger.Warn("invalid reportedInstanceTTL config: %s, fallback to %s",
		config.Cfg.Workflow.ReportedInstanceTTL, defaultReportedInstanceTTL)
	return defaultReportedInstanceTTL
}

// readReportedInstancesFromSnapshotLogs returns instances already written to recent
// snapshot logs of the given kind, with their event and window.
// Records without start_time are skipped; the newest record wins per instance.
// A query failure is fail-open: the caller still writes logs and alarms.
func (w *Workflow) readReportedInstancesFromSnapshotLogs(
	ctx context.Context,
	group *FailureGroup,
	kind reportLogKind,
) map[string]reportedSnapshotInstance {
	action := hamodel.SnapshotActionTypePreSwitch
	status := hamodel.DbSwitchingSnapshotLogStatusFailed
	if kind == reportLogNotifyOnly {
		action = hamodel.SnapshotActionTypeNotify
		status = hamodel.DbSwitchingSnapshotLogStatusSuccess
	}

	queryCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	defer cancel()

	ttl := reportedInstanceTTL()
	records, err := w.hadata.ListRecentSnapshotLogs(queryCtx, storage.RecentSnapshotLogQuery{
		BkBizID:   group.BkBizID,
		BkCloudID: group.BkCloudID,
		Action:    action,
		Status:    status,
		Since:     time.Now().Add(-ttl),
	})
	if err != nil {
		logger.Warn("failed to query recently reported snapshot logs, bizId: %d, action: %s, errmsg: %s",
			group.BkBizID, action, err)
		return map[string]reportedSnapshotInstance{}
	}

	result := make(map[string]reportedSnapshotInstance)
	for _, record := range records {
		if !record.Instances.Valid {
			continue
		}
		if record.StartTime == nil {
			logger.Warn("snapshot log record has no start time, skip it, bizId: %d, id: %d",
				group.BkBizID, record.ID)
			continue
		}
		dbType := haprobe.DbType(record.DbType)
		for _, inst := range record.Instances.Data {
			if inst == nil {
				continue
			}
			key := reportCacheKey(group.BkBizID, group.BkCloudID, inst.IP, inst.Port, dbType)
			// Keep the newest record so the inherited window has the longest remaining time.
			if existing, ok := result[key]; ok && !record.StartTime.After(existing.StartTime) {
				continue
			}
			result[key] = reportedSnapshotInstance{
				EventName: haprobe.DbEventName(inst.EventName),
				StartTime: *record.StartTime,
				TTL:       ttl,
			}
		}
	}
	return result
}

// buildReportEventsForInstances builds cache events keyed by failure instance.
func buildReportEventsForInstances(
	bkBizID int,
	dbType haprobe.DbType,
	instances []FailureInstanceInfo,
) map[string]haprobe.DbEventName {
	events := make(map[string]haprobe.DbEventName, len(instances))
	for i := range instances {
		inst := &instances[i]
		key := reportCacheKey(bkBizID, inst.BkCloudID, inst.IP, inst.Port, dbType)
		events[key] = inst.EventName
	}
	return events
}

// buildReportEventsForMetas builds cache events for metadata instances. Instances that
// are not part of the failure group keep an empty event, so a later failure is allowed.
func buildReportEventsForMetas(
	bkBizID int,
	dbType haprobe.DbType,
	group *FailureGroup,
	metas []*dbm.DbInstMetadata,
) map[string]haprobe.DbEventName {
	failureEvents := buildReportEventsForInstances(bkBizID, dbType, group.Instances)
	events := make(map[string]haprobe.DbEventName, len(metas))
	for _, meta := range metas {
		key := reportCacheKey(bkBizID, meta.BkCloudID, meta.IP, meta.Port, dbType)
		events[key] = failureEvents[key]
	}
	return events
}

// buildReportEntries prepares cache entries for every instance in this round. Only
// instances whose snapshot log event matches the current event inherit that log's window;
// the others start a new window from now.
func buildReportEntries(
	reportEvents map[string]haprobe.DbEventName,
	reported map[string]reportedSnapshotInstance,
	now time.Time,
) map[string]ReportCacheEntry {
	ttl := reportedInstanceTTL()
	entries := make(map[string]ReportCacheEntry, len(reportEvents))
	for key, event := range reportEvents {
		entry := ReportCacheEntry{EventName: event, SetAt: now, ExpireAt: now.Add(ttl)}
		if record, ok := reported[key]; ok && matchReportedEvent(record, event) {
			entry.SetAt = record.StartTime
			entry.ExpireAt = record.StartTime.Add(record.TTL)
		}
		entries[key] = entry
	}
	return entries
}

// logReportedCacheMark writes a per-instance log for every entry written by MarkReported.
// All time fields come from the entry, so the log matches the cache exactly.
func logReportedCacheMark(
	group *FailureGroup,
	reported map[string]reportedSnapshotInstance,
	entries map[string]ReportCacheEntry,
	now time.Time,
) {
	for key, entry := range entries {
		info := ReportCheckInfo{
			Inst:      key,
			Event:     entry.EventName,
			SetAt:     entry.SetAt,
			ExpireAt:  entry.ExpireAt,
			TTL:       entry.ExpireAt.Sub(entry.SetAt),
			Remaining: entry.ExpireAt.Sub(now).Round(time.Second),
			Reason:    reportReasonNoKey,
			Source:    reportSourceCache,
		}
		if record, ok := reported[key]; ok && matchReportedEvent(record, entry.EventName) {
			info.CachedEvent = record.EventName
			info.Reason = reportReasonHit
			info.Source = reportSourceDB
			logReported("restore reported instance cache from snapshot logs", info,
				group.BkBizID, group.DbType)
			continue
		}
		logReported("record newly reported instance cache", info, group.BkBizID, group.DbType)
	}
}

// excludeAlreadyReportedForInstances removes instances whose snapshot log event matches
// the current event. A changed event must be reported again.
func excludeAlreadyReportedForInstances(
	bkBizID int,
	dbType haprobe.DbType,
	instances []FailureInstanceInfo,
	reported map[string]reportedSnapshotInstance,
	reportEvents map[string]haprobe.DbEventName,
) []FailureInstanceInfo {
	filtered := make([]FailureInstanceInfo, 0, len(instances))
	for i := range instances {
		inst := &instances[i]
		key := reportCacheKey(bkBizID, inst.BkCloudID, inst.IP, inst.Port, dbType)
		if record, ok := reported[key]; ok && matchReportedEvent(record, reportEvents[key]) {
			continue
		}
		filtered = append(filtered, *inst)
	}
	return filtered
}

// excludeAlreadyReportedForMetas removes metadata instances whose snapshot log event
// matches the current event. A changed event must be reported again.
func excludeAlreadyReportedForMetas(
	bkBizID int,
	dbType haprobe.DbType,
	metas []*dbm.DbInstMetadata,
	reported map[string]reportedSnapshotInstance,
	reportEvents map[string]haprobe.DbEventName,
) []*dbm.DbInstMetadata {
	filtered := make([]*dbm.DbInstMetadata, 0, len(metas))
	for _, meta := range metas {
		key := reportCacheKey(bkBizID, meta.BkCloudID, meta.IP, meta.Port, dbType)
		if record, ok := reported[key]; ok && matchReportedEvent(record, reportEvents[key]) {
			continue
		}
		filtered = append(filtered, meta)
	}
	return filtered
}

// notifyGroupWithInstances creates a shallow copy of the group with replaced instances.
func notifyGroupWithInstances(group *FailureGroup, instances []FailureInstanceInfo) *FailureGroup {
	copied := *group
	copied.Instances = instances
	return &copied
}
