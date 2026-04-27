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
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
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
	readBatchCount       = 1000
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
}

// New creates a workflow instance. discovery and registryPrefix are used to list and watch
// same-module analysis instances for business sharding; myServiceID is this instance's ID.
func New(cli *discovery.Client, db *hamysql.GormDB, disc *discovery.Discovery,
	registryPrefix string, myServiceID string) (*Workflow, error) {

	wflow := &Workflow{
		hadata: &storage.DbhaData{
			DB: db,
		},

		dbmSync: &Synchronizer{
			db:           db,
			discoveryCli: cli,
			myServiceID:  myServiceID,
		},

		switchers: map[haprobe.DbType]switcher.Switcher{
			haprobe.DbTypeMySql: &switcher.Mysql{},
		},

		discoveryCli:   cli,
		discovery:      disc,
		registryPrefix: registryPrefix,
		myServiceID:    myServiceID,
		quit:           make(chan struct{}, 1),
	}

	wflow.alarm = NewAlarmNotifier()
	wflow.instanceDiscovery = NewInstanceDiscovery(wflow.discovery, wflow.registryPrefix,
		wflow.myServiceID, wflow.quit)

	wflow.windowMgr = NewBizWindowManager(config.Cfg.Workflow.WindowDuration, config.Cfg.Workflow.InflightTTL)
	wflow.metadataReader = NewMetadataReader(wflow.hadata, wflow.discoveryCli, myServiceID)
	wflow.switchExecutor = NewSwitchExecutor(wflow.hadata, wflow.dbmSync, wflow.switchers, myServiceID)
	wflow.detectorHandler = NewDetectorHandler(wflow.alarm, wflow.windowMgr, myServiceID)
	wflow.businessChecker = NewBusinessChecker(&wflow.StatusParser, wflow.detectorHandler)

	return wflow, nil
}

// Run runs the workflow: starts dbm sync, instance watch, and the periodic business scan loop.
func (w *Workflow) Run(ctx context.Context) error {
	if config.Cfg.Workflow.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small, reset it to the default value(%v)",
			config.Cfg.Workflow.ScanInterval, scanIntervalLimitMin)

		config.Cfg.Workflow.ScanInterval = scanIntervalLimitMin
	}

	if config.Cfg.Workflow.PopInterval < popIntervalLimitMin {
		logger.Warn("pop interval(%v) is too small, reset it to the default value(%v)",
			config.Cfg.Workflow.PopInterval, popIntervalLimitMin)

		config.Cfg.Workflow.PopInterval = popIntervalLimitMin
	}

	if err := w.dbmSync.Run(ctx); err != nil {
		logger.Error("failed to run the dbm metadata manager, errmsg: %v", err)
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
				logger.Debug("the workflow begins to scan the businesses")
				w.ScanBusinesses(ctx)
				logger.Debug("the workflow will scan the businesses, after: %v", config.Cfg.Workflow.ScanInterval)
				timer.Reset(config.Cfg.Workflow.ScanInterval)
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

	return nil
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
	if err := apm.ScanBusinessTimeConsumingMs.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}).Observe(float64(time.Since(start).Milliseconds())); err != nil {
		logger.Warn("failed to report the scan business time consuming, errmsg: %s", err)
	}

	// report the scan business total
	if err := apm.ScanBusinessTotal.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}).Add(float64(len(assigned))); err != nil {
		logger.Warn("failed to report the scan business total, errmsg: %s", err)
	}
}

// PopAndSwitch iterates over assigned business IDs, pops matured entries from sliding windows,
// matches switching strategies, and triggers switching for matched groups.
// Each business acquires an independent SwitchLock to prevent multiple AM instances from
// switching the same business simultaneously. SwitchLock is independent of ScanLock.
func (w *Workflow) PopAndSwitch(ctx context.Context) {
	start := time.Now()

	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	bizIDs, err := w.hadata.GetBizIDs(qCtx)
	cancel()
	if err != nil {
		logger.Warn("failed to get business IDs for pop-switch, errmsg: %s", err)
		return
	}

	assigned := w.instanceDiscovery.AssignedBizIDs(bizIDs)
	wg := sync.WaitGroup{}
	sem := make(chan struct{}, 10)

	for _, bizID := range assigned {
		sem <- struct{}{}
		wg.Add(1)

		go func(bizId int) {
			defer wg.Done()
			defer func() { <-sem }()

			safe.Run(func() {
				w.popAndSwitchForBiz(ctx, bizId)
			}, safe.WithLabel("PopAndSwitch"))
		}(bizID)
	}

	wg.Wait()

	// report the pop-switch time consuming
	if err := apm.PopSwitchTimeConsumingMs.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}).Observe(float64(time.Since(start).Milliseconds())); err != nil {
		logger.Warn("failed to report the pop-switch time consuming, errmsg: %s", err)
	}

	// report the pop-switch business total
	if err := apm.PopSwitchBusinessTotal.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   w.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}).Add(float64(len(assigned))); err != nil {
		logger.Warn("failed to report the pop-switch business total, errmsg: %s", err)
	}
}

// popAndSwitchForBiz performs pop-and-switch for a single business:
// acquires SwitchLock, pops matured entries, marks all instances as inflight,
// groups by (BkCloudID, DbType), matches strategies, and triggers switching or notification.
func (w *Workflow) popAndSwitchForBiz(ctx context.Context, bizId int) {
	_, unlock, err := w.metadataReader.AcquireSwitchLock(ctx, bizId)
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
			logger.Error("panic in popAndSwitchForBiz, bizId: %d, errmsg: %v", bizId, pi.Reason)
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

	matched, strategy := w.switchExecutor.MatchStrategyForGroup(ctx, group)
	if !matched {
		logger.Info(
			"no matching switching strategy, skip, cloudId: %d, dbType: %s, instances: %d, events: [%s]",
			group.BkCloudID,
			group.DbType,
			len(group.Instances),
			FormatInstanceEventSummary(group.Instances),
		)
		return
	}

	if w.handleStrategyNotify(strategy, group) {
		return
	}

	w.filterWhitelistedInstances(ctx, group, req)
	if !req.HasDbInstMetadata() {
		logger.Info("all instances are whitelisted, notify only, cloudId: %d, dbType: %s",
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

// filterWhitelistedInstances filters out instances that are in the whitelist from the switch request.
// Whitelisted instances are removed from the request and a notification alarm is sent for them.
// The remaining instances will continue through the normal strategy matching and switching flow.
func (w *Workflow) filterWhitelistedInstances(ctx context.Context, group *FailureGroup, req *switcher.Request) {
	if !config.Cfg.Workflow.EnableSwitching {
		logger.Warn("switching operation is disabled, skip filtering whitelisted instances")
		return
	}

	bkBizID := group.Instances[0].BkBizID

	qCtx, cancel := context.WithTimeout(ctx, config.Cfg.Storage.Timeout)
	defer cancel()

	whiteList, err := w.hadata.ReadBlackWhiteList(qCtx, bkBizID, group.BkCloudID)
	if err != nil {
		logger.Warn("failed to read the black-white list, bkBizId: %d, bkCloudId: %d, errmsg: %s",
			bkBizID, group.BkCloudID, err)
		return
	}

	if len(whiteList) == 0 {
		return
	}

	whiteListMap := make(map[int]*hamodel.DbBlackWhiteList, len(whiteList))
	for _, item := range whiteList {
		whiteListMap[item.ClusterID] = item
	}

	whitelistedMetas := make([]*dbm.DbInstMetadata, 0)
	remaining := make([]*dbm.DbInstMetadata, 0)

	for _, meta := range req.MySqlInstData {
		if _, exists := whiteListMap[meta.ClusterID]; exists {
			logger.Info("instance is in the whitelist, skip switching, clusterId: %d, clusterName: %s, ip: %s, port: %d",
				meta.ClusterID, meta.Cluster, meta.IP, meta.Port)
			whitelistedMetas = append(whitelistedMetas, meta)
			continue
		}
		remaining = append(remaining, meta)
	}

	if len(whitelistedMetas) == 0 {
		return
	}

	req.MySqlInstData = remaining

	// if there are whitelisted instances, send a notification alarm
	clusterInfos := make([]string, 0, len(whitelistedMetas))
	for _, meta := range whitelistedMetas {
		clusterInfos = append(clusterInfos, fmt.Sprintf("%d:%s", meta.ClusterID, meta.Cluster))
	}
	log := fmt.Sprintf(
		"found %d whitelisted instance(s), execute notification only, bkBizId: %d, bkCloudId: %d, dbType: %s, clusters: [%s]",
		len(whitelistedMetas), bkBizID, group.BkCloudID, group.DbType, strings.Join(clusterInfos, ", "))
	logger.Info("%s", log)
	w.alarm.TriggerWithBizId(bkBizID, log)
}

func (w *Workflow) handleStrategySwitch(strategy *hamodel.DbSwitchingStrategy, group *FailureGroup, req *switcher.Request) bool {
	if strategy.Action != hamodel.ActionTypeSwitch {
		return false
	}

	req.ActionScope = strategy.Scope
	req.SwitchID = generateSwitchID()

	logger.Info("trigger switching by strategyId: %d, switchId: %s, dbType: %s, cloudId: %d, instances: %d",
		strategy.ID, req.SwitchID, group.DbType, group.BkCloudID, len(group.Instances))

	w.switchExecutor.TriggerSwitching(group.DbType, req)

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
