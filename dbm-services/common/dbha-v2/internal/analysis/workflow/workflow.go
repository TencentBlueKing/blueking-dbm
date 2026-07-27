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

// Package workflow provides the core workflow engine for DBHA.
package workflow

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/google/uuid"
)

var (
	ErrCreateMutexFailure    = gerrors.Newf(gerrors.EtcdFailure, "failed to create a mutex for a business")
	ErrReadMetadataFailure   = gerrors.Newf(gerrors.MysqlFailure, "failed to read metadata")
	ErrReadDbMetricFailure   = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB metrics")
	ErrReadDbEventFailure    = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB event")
	ErrReadSkipDbInstFailure = gerrors.Newf(gerrors.MysqlFailure, "failed to read skip db-inst")
	ErrAcquireLockFailure    = gerrors.Newf(gerrors.EtcdFailure, "failed to acquire the lock for the business")
	ErrDetectorFailure       = gerrors.Newf(gerrors.Failure, "detector failure, switching is needed")
)

const (
	scanIntervalLimitMin = 5 * time.Second
	popIntervalLimitMin  = 5 * time.Second
	dbTableStatsInterval = 5 * time.Minute
	readBatchCount       = 1000
	popSwitchSemSize     = 10
)

// Workflow represents the workflow engine for DBHA.
// It is composed of instance discovery, alarm, metadata, switch, detector, and checker.
// It manages two independent periodic loops: scan (detecting failures and pushing to windows)
// and pop-switch (popping matured entries from windows and triggering switching).
type Workflow struct {
	StatusParser

	hadata            *storage.DbhaData
	dbmSync           *Synchronizer
	discoveryCli      *discovery.Client
	discovery         *discovery.Discovery
	registryPrefix    string
	myServiceID       string
	switchers         map[haprobe.DbType]switcher.Switcher
	quit              chan struct{}
	wg                sync.WaitGroup
	instanceDiscovery *InstanceDiscovery
	alarm             *AlarmNotifier
	metadataReader    *MetadataReader
	switchExecutor    *SwitchExecutor
	detectorHandler   *DetectorHandler
	businessChecker   *BusinessChecker
	windowMgr         *BizWindowManager
	popSwitchSem      chan struct{}
	lockTracker       *InProcessLockTracker // makes the per-biz etcd switch lock reentrant within this AM
	swSnapshotLogger  logger.Logger         // switching-snapshot-* log file; nil disables file snapshots
}

// New creates a workflow instance. discovery and registryPrefix are used to list and watch
// same-module analysis instances for business sharding; myServiceID is this instance's ID.
func New(cli *discovery.Client, db *hamysql.GormDB, disc *discovery.Discovery,
	registryPrefix string, myServiceID string, swSnapshotLogger logger.Logger) (*Workflow, error) {

	wflow := &Workflow{
		hadata: &storage.DbhaData{
			DB: db,
		},

		dbmSync: &Synchronizer{
			db:           db,
			discoveryCli: cli,
			myServiceID:  myServiceID,
		},

		switchers: switcher.Build(),

		discoveryCli:     cli,
		discovery:        disc,
		registryPrefix:   registryPrefix,
		myServiceID:      myServiceID,
		swSnapshotLogger: swSnapshotLogger,
		quit:             make(chan struct{}, 1),
	}

	wflow.alarm = NewAlarmNotifier()
	wflow.instanceDiscovery = NewInstanceDiscovery(wflow.discovery, wflow.registryPrefix,
		wflow.myServiceID, wflow.quit)

	wflow.windowMgr = NewBizWindowManager(config.Cfg.Workflow.WindowDuration, config.Cfg.Workflow.InflightTTL, myServiceID)
	wflow.metadataReader = NewMetadataReader(wflow.hadata, wflow.discoveryCli, myServiceID)
	wflow.switchExecutor = NewSwitchExecutor(wflow.hadata, wflow.dbmSync, wflow.switchers, myServiceID)
	wflow.detectorHandler = NewDetectorHandler(wflow.alarm, wflow.windowMgr, myServiceID)
	wflow.businessChecker = NewBusinessChecker(&wflow.StatusParser, wflow.detectorHandler)

	semSize := config.Cfg.Workflow.PopSwitchSemSize
	if semSize <= 0 {
		logger.Warn("the pop-switch semaphore size(%d) is too small, reset it to the default value(%d)",
			semSize, popSwitchSemSize)
		semSize = popSwitchSemSize
	}
	logger.Info("the pop-switch semaphore size is: %d", semSize)
	wflow.popSwitchSem = make(chan struct{}, semSize)
	wflow.lockTracker = NewInProcessLockTracker()

	return wflow, nil
}

// Run runs the workflow: starts dbm sync, instance watch, and the periodic business scan loop.
func (w *Workflow) Run(ctx context.Context) error {
	clampIntervalToMin("scan", &config.Cfg.Workflow.ScanInterval, scanIntervalLimitMin)
	clampIntervalToMin("pop", &config.Cfg.Workflow.PopInterval, popIntervalLimitMin)

	if err := w.dbmSync.Run(ctx); err != nil {
		logger.Error("failed to run dbm metadata manager, errmsg: %s", err)
		return err
	}

	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		w.instanceDiscovery.RunWatch(ctx)
	}()

	// Scan timer: periodically scan businesses, detect failures and push into sliding windows
	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(config.Cfg.Workflow.ScanInterval)
		defer timer.Stop()

		for {
			select {
			case <-w.quit:
				logger.Info("the scan loop exited(quit)")
				return

			case <-ctx.Done():
				logger.Info("the scan loop exited(ctx done)")
				return

			case <-timer.C:
				timer.Reset(config.Cfg.Workflow.ScanInterval)
				logger.Debug("the workflow begins to scan the businesses, next scan after: %v", config.Cfg.Workflow.ScanInterval)
				w.ScanBusinesses(ctx)
			}
		}
	}()

	// Switch timer: periodically pop matured entries from sliding windows, match strategies and trigger switching
	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(config.Cfg.Workflow.PopInterval)
		defer timer.Stop()

		for {
			select {
			case <-w.quit:
				logger.Info("the pop-switch loop exited(quit)")
				return

			case <-ctx.Done():
				logger.Info("the pop-switch loop exited(ctx done)")
				return

			case <-timer.C:
				logger.Debug("the workflow begins to pop and switch")
				w.PopAndSwitch(ctx)
				logger.Debug("the workflow will pop and switch, after: %v", config.Cfg.Workflow.PopInterval)
				timer.Reset(config.Cfg.Workflow.PopInterval)
			}
		}
	}()

	// DB table update stats timer: periodically count rows updated within dbTableStatsInterval,
	// grouped by db_type, and report as gauges.
	w.wg.Add(1)
	go w.runDbTableStatsLoop(ctx)

	return nil
}

// runDbTableStatsLoop periodically counts rows updated within dbTableStatsInterval
// in the DbmMetadata and DbhaDataStatus tables, grouped by db_type,
// and reports them as gauges. It exits on workflow quit or ctx cancellation.
func (w *Workflow) runDbTableStatsLoop(ctx context.Context) {
	defer w.wg.Done()

	timer := time.NewTimer(dbTableStatsInterval)
	defer timer.Stop()

	for {
		select {
		case <-w.quit:
			logger.Info("the db table stats loop exited(quit)")
			return

		case <-ctx.Done():
			logger.Info("the db table stats loop exited(ctx done)")
			return

		case <-timer.C:
			w.reportDbTableUpdatedStats(ctx)
			timer.Reset(dbTableStatsInterval)
		}
	}
}

// clampIntervalToMin ensures the given interval is not smaller than the allowed minimum.
// If it is, a warning is emitted and the interval is reset to the minimum in place.
// name is used to label the interval in the log message (e.g. "scan", "pop").
func clampIntervalToMin(name string, current *time.Duration, min time.Duration) {
	if *current >= min {
		return
	}

	logger.Warn("%s interval(%v) is too small, reset it to the default value(%v)",
		name, *current, min)
	*current = min
}

// Close closes the workflow.
func (w *Workflow) Close() {
	if w.quit != nil {
		close(w.quit)
	}

	w.wg.Wait()
	w.quit = nil
}

// CheckBusinessWithBizID checks a business by its ID.
// It acquires scan lock, reads metadata and status, and runs checks via BusinessChecker.
func (w *Workflow) CheckBusinessWithBizID(ctx context.Context, bizId int) error {
	logger.Debug("scan the business: %d", bizId)

	_, unlock, err := w.metadataReader.AcquireScanLock(ctx, bizId)
	if err != nil {
		return err
	}
	defer unlock()

	bizMeta, err := w.metadataReader.ReadBusinessMetadata(bizId)
	if err != nil {
		return err
	}

	// Whitelist filter for scan: only instances in whitelisted clusters are probed.
	// This step is independent of the later t_skip_dbinstance-based skip filtering in RunBusinessChecks.
	if err := w.filterByWhitelistForScan(ctx, bizId, bizMeta); err != nil {
		return err
	}

	if len(bizMeta.Conds) == 0 {
		logger.Debug("no whitelisted instances to scan, bizId: %d", bizId)
		return nil
	}

	dbStatus, err := w.metadataReader.ReadDbStatusWithInstances(
		bizMeta.Conds,
		config.Cfg.Workflow.ReadDbMetricOffsetDuration,
	)
	if err != nil {
		logger.Warn("failed to read the DB status with the conditions: %v, bizId: %d, errmsg: %s", bizMeta.Conds, bizId, err)
		return ErrReadDbMetricFailure
	}

	statusData := w.metadataReader.ExtractDbStatusData(dbStatus)

	skipInsts, err := w.metadataReader.ReadBusinessSkipInstances(bizId)
	if err != nil {
		return err
	}

	w.businessChecker.RunBusinessChecks(bizId, dbStatus, statusData, skipInsts, bizMeta.MetaInsts)

	logger.Debug("finished scanning the business: %d", bizId)
	return nil
}

// ScanBusinesses fetches business IDs, filters by instance sharding,
// and runs CheckBusinessWithBizID for each (with concurrency limit).
func (w *Workflow) ScanBusinesses(ctx context.Context) {
	start := time.Now()

	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	bizIDs, err := w.hadata.GetBizIDs(qCtx)
	cancel()
	if err != nil {
		logger.Warn("failed to get business IDs, errmsg: %s", err)
		return
	}

	assigned := w.instanceDiscovery.AssignedBizIDs(bizIDs)

	// Report the business total
	if err := apm.AmBusinessTotal.SetWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(len(assigned))); err != nil {
		logger.Warn("failed to report the business total, errmsg: %s", err)
	}

	wg := sync.WaitGroup{}
	sem := make(chan struct{}, 10)

	for _, bizID := range assigned {
		sem <- struct{}{}
		wg.Add(1)

		go func(bizId int) {
			defer wg.Done()
			defer func() { <-sem }()

			safe.Run(func() {
				err := w.CheckBusinessWithBizID(ctx, bizId)
				if err == nil {
					logger.Info("successfully complete the business check, bizId: %d", bizId)
					return
				}

				logger.Warn("failed to check the business, bizId: %d", bizId)
				w.alarm.TriggerWithBizId(bizId, err.Error())
			}, safe.WithLabel("ScanBusinesses"))
		}(bizID)
	}

	wg.Wait()

	// report the scan business time consuming
	if err := apm.ScanBusinessTimeConsumingMs.ObserveWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(time.Since(start).Milliseconds())); err != nil {
		logger.Warn("failed to report the scan business time consuming, errmsg: %s", err)
	}

	// report the scan business total
	if err := apm.ScanBusinessTotal.AddWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(len(assigned))); err != nil {
		logger.Warn("failed to report the scan business total, errmsg: %s", err)
	}
}

// PopAndSwitch iterates over assigned business IDs, pops matured entries from sliding windows,
// matches switching strategies, and triggers switching for matched groups.
// Each business acquires an independent SwitchLock to prevent multiple AM instances from
// switching the same business simultaneously. SwitchLock is independent of ScanLock.
func (w *Workflow) PopAndSwitch(ctx context.Context) {
	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	bizIDs, err := w.hadata.GetBizIDs(qCtx)
	cancel()
	if err != nil {
		logger.Warn("failed to get business IDs for pop-switch, errmsg: %s", err)
		return
	}

	assigned := w.instanceDiscovery.AssignedBizIDs(bizIDs)

	for _, bizID := range assigned {
		select {
		case w.popSwitchSem <- struct{}{}:
		default:
			logger.Debug("popSwitchSem is full, waiting for a slot, bizId: %d", bizID)
			w.popSwitchSem <- struct{}{}
		}

		go func(bizId int) {
			defer func() { <-w.popSwitchSem }()

			safe.Run(func() {
				w.popAndSwitchForBiz(ctx, bizId)
			}, safe.WithLabel("PopAndSwitch"))
		}(bizID)
	}

	// report the sliding window size
	apm.SlidingWindowSize.Clear()
	for _, bizId := range assigned {
		if err := apm.SlidingWindowSize.SetWithLabels(map[string]string{
			haapm.MetricLabelServiceID:   w.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
			apm.MetricLabelBizID:         strconv.Itoa(bizId),
		}, float64(w.windowMgr.WindowLen(bizId))); err != nil {
			logger.Warn("failed to report sliding window size, bizId: %d, errmsg: %s", bizId, err)
		}
	}

	// report the pop-switch business total
	if err := apm.PopSwitchBusinessTotal.AddWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(len(assigned))); err != nil {
		logger.Warn("failed to report the pop-switch business total, errmsg: %s", err)
	}
}

// popAndSwitchForBiz runs one switching pass for a single business:
// acquires the switch lock via lockTracker (reentrant within this AM, mutually
// exclusive across AMs), pops matured entries, marks instances as inflight,
// groups by (BkCloudID, DbType), and dispatches each group for switching.
func (w *Workflow) popAndSwitchForBiz(ctx context.Context, bizId int) {
	start := time.Now()
	defer func() {
		// report the pop-switch business time consuming
		if err := apm.PopSwitchTimeConsumingMs.ObserveWithLabels(map[string]string{
			haapm.MetricLabelServiceID:   w.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
		}, float64(time.Since(start).Milliseconds())); err != nil {
			logger.Warn("failed to report the pop-switch time consuming, errmsg: %s", err)
		}
	}()

	unlock, err := w.lockTracker.Acquire(ctx, w.metadataReader, bizId)
	if err != nil {
		logger.Debug("skip pop-switch for biz %d, unable to acquire switch lock, errmsg: %s", bizId, err)
		return
	}
	defer unlock()

	entries := w.windowMgr.PopAndMarkStart(bizId, time.Now())
	if len(entries) == 0 {
		return
	}

	logger.Info("popped %d matured entries for biz %d", len(entries), bizId)
	groups := groupEntriesByCloudAndDbType(entries)

	var failureGroupFns []func()
	for _, group := range groups {
		failureGroupFns = append(failureGroupFns, func() {
			w.handleFailureGroup(ctx, group)
		})
	}

	wait := safe.GoWaits(failureGroupFns,
		safe.WithLabel("popAndSwitchForBiz"), safe.WithOnPanic(func(pi safe.PanicInfo) {
			logger.Error("panic in pop and switch for biz, biz_id: %d, errmsg: %s", bizId, pi.Reason)
		}))

	wait()
}

func (w *Workflow) handleFailureGroup(ctx context.Context, group *FailureGroup) {
	groupInstKeys := collectGroupInstanceKeys(group)
	defer w.markDoneAll(groupInstKeys)

	req := w.switchExecutor.CreateRequestWithGroup(ctx, group)

	if req == nil {
		return
	}

	if !req.HasDbInstMetadata() {
		logger.Warn("no db inst metadata after query, dbType: %s, cloudId: %d, instances: %d",
			group.DbType, group.BkCloudID, len(group.Instances))
		return
	}

	// Build switchGroup with only the instances still reported available by DBM, so strategy
	// matching counts the actually-switchable ones instead of stale failures. The original group
	// remains the source of truth for downstream logging and inflight cleanup.
	switchGroup := &FailureGroup{
		BkCloudID: group.BkCloudID,
		DbType:    group.DbType,
		Instances: excludeUnavailableInstances(group.Instances, req),
	}
	matched, strategy := w.switchExecutor.MatchStrategyForGroup(ctx, switchGroup)
	if !matched {
		logger.Info(
			"no matching switching strategy, skip, cloudId: %d, dbType: %s, instances: %d (matched: %d), events: [%s]",
			group.BkCloudID,
			group.DbType,
			len(group.Instances),
			len(switchGroup.Instances),
			FormatInstanceEventSummary(group.Instances),
		)
		return
	}

	if w.handleStrategyNotify(strategy, group) {
		return
	}

	// Whitelist filter for switch: scan-time whitelist filtering does not cover every switch path.
	// On a host with multiple instances, a fault on a non-whitelisted instance may still enter switching,
	// so we filter fault instances again here before executing switch.
	if err := w.filterByWhitelistForSwitch(ctx, group, req); err != nil {
		logger.Warn("skip switch because whitelist filter failed, cloudId: %d, dbType: %s, errmsg: %s",
			group.BkCloudID, group.DbType, err)
		return
	}
	if !req.HasDbInstMetadata() {
		logger.Info("no whitelisted instances remain, notify only, cloudId: %d, dbType: %s",
			group.BkCloudID, group.DbType)
		return
	}

	if w.handleStrategySwitch(strategy, group, req) {
		return
	}

	logger.Warn("unknown strategy action: %s, strategyId: %d, cloudId: %d, dbType: %s",
		strategy.Action, strategy.ID, group.BkCloudID, group.DbType)
}

func collectGroupInstanceKeys(group *FailureGroup) []string {
	groupInstKeys := make([]string, 0, len(group.Instances))
	for _, inst := range group.Instances {
		groupInstKeys = append(groupInstKeys,
			instanceWindowKey(inst.BkCloudID, inst.IP, inst.Port, inst.DbType))
	}

	return groupInstKeys
}

func (w *Workflow) handleStrategyNotify(strategy *hamodel.DbSwitchingStrategy, group *FailureGroup) bool {
	if strategy.Action != hamodel.ActionTypeNotify {
		return false
	}

	log := fmt.Sprintf("strategy action is %s, execute notification, strategyId: %d, cloudId: %d, dbType: %s",
		strategy.Action, strategy.ID, group.BkCloudID, group.DbType)
	logger.Info("%s", log)

	w.alarm.TriggerWithBizId(group.Instances[0].BkBizID, log)
	return true
}

func (w *Workflow) handleStrategySwitch(strategy *hamodel.DbSwitchingStrategy, group *FailureGroup, req *switcher.Request) bool {
	if strategy.Action != hamodel.ActionTypeSwitch {
		return false
	}

	req.ActionScope = strategy.Scope
	req.SwitchID = generateSwitchID()

	logger.Info("trigger switching by strategyId: %d, switchId: %s, dbType: %s, cloudId: %d, instances: %d",
		strategy.ID, req.SwitchID, group.DbType, group.BkCloudID, len(group.Instances))

	// Report the triggering switching instance total
	if err := apm.TriggerSwitchingInstanceTotal.AddWithLabels(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(len(req.InstData))); err != nil {
		logger.Warn("failed to update switching instance total metric, errmsg: %s", err)
	}

	// Build the switching snapshot data
	snapshotData := NewSwitchingSnapshotData(strategy, group, req, w.swSnapshotLogger)
	if snapshotData == nil {
		logger.Warn("failed to create switching snapshot data, switchId: %s", req.SwitchID)
	}

	w.switchExecutor.TriggerSwitching(group.DbType, req, snapshotData)

	return true
}

// generateSwitchID generates a unique switch ID.
func generateSwitchID() string {
	return fmt.Sprintf("%s-%s", config.SwitchIDVersion, strings.ReplaceAll(uuid.New().String(), "-", ""))
}

// markDoneAll releases inflight marks for all the given instance keys.
func (w *Workflow) markDoneAll(keys []string) {
	for _, key := range keys {
		w.windowMgr.MarkDone(key)
	}
}

// groupEntriesByCloudAndDbType groups window entries by (BkCloudID, DbType) into FailureGroups
// for batch strategy matching and switching.
func groupEntriesByCloudAndDbType(entries []*FailureWindowEntry) []*FailureGroup {
	groupMap := make(map[string]*FailureGroup)
	var keys []string

	for _, entry := range entries {
		key := fmt.Sprintf("%d:%s", entry.BkCloudID, entry.DbType)
		if g, ok := groupMap[key]; ok {
			g.Instances = append(g.Instances, entry.FailureInstanceInfo)
		} else {
			groupMap[key] = &FailureGroup{
				BkCloudID: entry.BkCloudID,
				DbType:    entry.DbType,
				Instances: []FailureInstanceInfo{entry.FailureInstanceInfo},
			}
			keys = append(keys, key)
		}
	}

	// Maintain deterministic order
	sort.Strings(keys)
	groups := make([]*FailureGroup, 0, len(keys))
	for _, k := range keys {
		groups = append(groups, groupMap[k])
	}

	return groups
}

// instanceKey builds a unique instance identifier from cloud id, IP and port.
func instanceKey[T any](bkCloudId int, ip string, port T) string {
	return fmt.Sprintf("%d:%s:%v", bkCloudId, ip, port)
}

// reportDbTableUpdatedStats queries the DbmMetadata and DbhaDataStatus tables for
// rows updated within the last dbTableStatsInterval, grouped by db_type,
// and reports each group's count to the corresponding gauge metric.
func (w *Workflow) reportDbTableUpdatedStats(ctx context.Context) {
	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	defer cancel()

	// DbmMetadata
	metaCounts, err := w.hadata.CountDbmMetadataUpdatedWithin(qCtx, dbTableStatsInterval)
	if err != nil {
		logger.Warn("failed to count DbmMetadata updated rows, errmsg: %s", err)
		return
	}
	// Clear previous window's series so that instances that stopped updating won't keep their stale values.
	apm.DbmMetadataUpdatedCount.Clear()
	for _, item := range metaCounts {
		if item.DbType == haprobe.DbTypeNone {
			item.DbType = haprobe.DbTypeUnknown
		}
		if e := apm.DbmMetadataUpdatedCount.SetWithLabels(map[string]string{
			haapm.MetricLabelServiceID:   w.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
			apm.MetricLabelDbType:        item.DbType.String(),
		}, float64(item.Count)); e != nil {
			logger.Warn("failed to report dbm_metadata_updated_count, dbType: %s, errmsg: %s", item.DbType, e)
		}
	}

	// DbhaDataStatus
	statusCounts, err := w.hadata.CountDbhaDataStatusUpdatedWithin(qCtx, dbTableStatsInterval)
	if err != nil {
		logger.Warn("failed to count DbhaDataStatus updated rows, errmsg: %s", err)
		return
	}
	// Clear previous window's series so that instances that stopped updating won't keep their stale values.
	apm.DbhaDataStatusUpdatedCount.Clear()
	for _, item := range statusCounts {
		if item.DbType == haprobe.DbTypeNone {
			item.DbType = haprobe.DbTypeUnknown
		}
		if e := apm.DbhaDataStatusUpdatedCount.SetWithLabels(map[string]string{
			haapm.MetricLabelServiceID:   w.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
			apm.MetricLabelDbType:        item.DbType.String(),
		}, float64(item.Count)); e != nil {
			logger.Warn("failed to report dbha_data_status_updated_count, dbType: %s, errmsg: %s", item.DbType, e)
		}
	}
}
