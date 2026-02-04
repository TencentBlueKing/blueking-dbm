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
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
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
	readBatchCount       = 1000
)

// Workflow represents the workflow engine for DBHA, composed of instance discovery, alarm, metadata, switch, detector, and checker.
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

	wflow.metadataReader = NewMetadataReader(wflow.hadata, wflow.discoveryCli)
	wflow.switchExecutor = NewSwitchExecutor(wflow.hadata, wflow.dbmSync, wflow.switchers)
	wflow.detectorHandler = NewDetectorHandler(wflow.alarm, wflow.switchExecutor)
	wflow.businessChecker = NewBusinessChecker(&wflow.StatusParser, wflow.detectorHandler)

	return wflow, nil
}

// Run runs the workflow: starts dbm sync, instance watch, and the periodic business scan loop.
func (w *Workflow) Run(ctx context.Context) error {
	if config.Cfg.Workflow.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small,reset it to the default value(%v)",
			config.Cfg.Workflow.ScanInterval, scanIntervalLimitMin)

		config.Cfg.Workflow.ScanInterval = scanIntervalLimitMin
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

	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(config.Cfg.Workflow.ScanInterval)
		defer timer.Stop()

		for {
			select {
			case <-w.quit:
				logger.Info("the workflow exited(quit)")
				return

			case <-ctx.Done():
				logger.Info("the workflow exited(ctx done)")
				return

			case <-timer.C:
				logger.Debug("the workflow begins to scan the businesses")
				w.ScanBusinesses(ctx)
				logger.Debug("the workflow will scan the businesses, after: %v", config.Cfg.Workflow.ScanInterval)
				timer.Reset(config.Cfg.Workflow.ScanInterval)
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

// CheckBusinessWithBizID checks a business by its ID: acquires lock, reads metadata and status, runs checks via BusinessChecker.
func (w *Workflow) CheckBusinessWithBizID(ctx context.Context, bizId int) error {
	logger.Debug("check the business: %d", bizId)

	_, unlock, err := w.metadataReader.AcquireBusinessLock(ctx, bizId)
	if err != nil {
		return err
	}
	defer unlock()

	bizMeta, err := w.metadataReader.ReadBusinessMetadata(bizId)
	if err != nil {
		return err
	}

	dbStatus, err := w.hadata.ReadDbStatusWithDbInstances(bizMeta.Conds, config.Cfg.Workflow.ReadDbMetricOffsetDuration)
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

	logger.Debug("finished checking the business: %d", bizId)
	return nil
}

// ScanBusinesses fetches business IDs, filters by instance sharding,
// and runs CheckBusinessWithBizID for each (with concurrency limit).
func (w *Workflow) ScanBusinesses(ctx context.Context) {
	bizIDs, err := w.hadata.GetBizIDs()
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

			err := w.CheckBusinessWithBizID(ctx, bizId)
			if err == nil {
				logger.Info("successfully complete the business check, bizId: %d", bizId)
				return
			}

			logger.Warn("failed to check the business, bizId: %d", bizId)
			w.alarm.TriggerWithBizId(bizId, err.Error())
		}(bizID)
	}

	wg.Wait()
}

// instanceKey builds a unique instance identifier from cloud id, IP and port.
func instanceKey[T any](bkCloudId int, ip string, port T) string {
	return fmt.Sprintf("%d:%s:%v", bkCloudId, ip, port)
}
