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
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	scanIntervalLimitMin = 5 * time.Second
	readBatchCount       = 1000
)

type Workflow struct {
	hadata       *storage.DbhaData
	dbmMetadata  *DbmMetadata
	discoveryCli *discovery.Client
	switchers    map[haprobe.DbType]switcher.Switcher
	cfg          config.WorkflowConfig
	quit         chan struct{}
	wg           sync.WaitGroup
}

func New(cfg config.WorkflowConfig, cli *discovery.Client, db *hamysql.DB) (*Workflow, error) {
	wflow := &Workflow{
		hadata: &storage.DbhaData{
			DB: db,
		},

		dbmMetadata: &DbmMetadata{
			db:           db,
			discoveryCli: cli,
		},

		switchers: map[haprobe.DbType]switcher.Switcher{
			haprobe.DbTypeMysql: &switcher.Mysql{},
		},

		cfg:          cfg,
		discoveryCli: cli,
		quit:         make(chan struct{}, 1),
	}

	return wflow, nil
}

func (w *Workflow) breakdownRecovery(bizID int, metaInsts map[string]*hamodel.DbmMetadata,
	breakdownInsts map[string]*hamodel.DbmMetadata) {

	// TODO: Implement the switching logic for the breakdown database.
}

func (w *Workflow) databaseLivenessDoubleCheck(bizID int, metaInsts map[string]*hamodel.DbmMetadata,
	breakdownInsts map[string]*hamodel.DbmMetadata) {

	// TODO: Implement the double-check logic for the breakdown database.

	w.breakdownRecovery(bizID, metaInsts, breakdownInsts)
}

func (w *Workflow) checkEventWithBizID(bizID int, dbEvents []*hamodel.DbEvent,
	skipDbInsts map[string]*hamodel.SkipDbInstance, metaInsts map[string]*hamodel.DbmMetadata) {

	events := []*hamodel.DbEvent{}
	metas := []*hamodel.DbmMetadata{}

	for _, event := range dbEvents {
		key := fmt.Sprintf("%d:%s:%d", event.BkCloudID, event.IP, event.Port)

		if inst, exists := metaInsts[key]; exists {
			metas = append(metas, inst)
		}

		if _, exists := skipDbInsts[key]; exists {
			logger.Info("skip the db instance: %s", key)
			continue
		}

		events = append(events, event)
	}

	req := &switcher.Request{}
	req.BkBizID = bizID
	req.BreakdownEvents = events
	req.MetaInsts = metas

	w.switchers[haprobe.DbTypeMysql].Switch(context.Background(), req)
}

func (w *Workflow) checkMissedProbeWithBizID(bizID int, dbMetrics []*hamodel.DatabaseMetric,
	skipDbInsts map[string]*hamodel.SkipDbInstance, metaInsts map[string]*hamodel.DbmMetadata) {

	insts := metaInsts

	// Delete the existing keys.
	for _, dbMetric := range dbMetrics {
		ips := strings.SplitSeq(dbMetric.IPs, constant.Delimiter)

		for ip := range ips {
			key := fmt.Sprintf("%d:%s:%s", dbMetric.BkCloudID, ip, dbMetric.InstanceID)

			if _, exists := metaInsts[key]; exists {
				delete(insts, key)
			}

			if _, exists := skipDbInsts[key]; exists {
				logger.Info("skip the db instance: %s", key)
				delete(insts, key)
			}
		}
	}

	// Post the alarm event by the bk-monitor.
	for _, metaInst := range insts {
		target := fmt.Sprintf("%d:%s:%d", metaInst.BkCloudID, metaInst.IP, metaInst.Port)
		monitorEvent := &monitor.EventData{
			Name:      haprobe.DbEventNameProbeOffline.String(),
			Target:    target,
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		monitorEvent.Content.Content = fmt.Sprintf("%s missed probe", target)
		monitorEvent.Dimension.IP = metaInst.IP
		monitorEvent.Dimension.Port = metaInst.Port
		monitorEvent.Dimension.DbClusterType = metaInst.ClusterType
		monitorEvent.Dimension.DbMachineType = metaInst.MachineType
		monitorEvent.Dimension.DbEventName = haprobe.DbEventNameProbeOffline
		monitorEvent.Dimension.DbEventNameReason = haprobe.DbEventNameReasonMissedProbe

		if err := monitor.PostBKMonitor(10*time.Second, monitorEvent); err != nil {
			logger.Warn("%v", err)
		}
	}

	w.databaseLivenessDoubleCheck(bizID, metaInsts, insts)
}

func (w *Workflow) checkDbMetricWithBizID(ctx context.Context, bizID int, dbMetrics []*hamodel.DatabaseMetric) {
	// TODO:
}

func (w *Workflow) checkBusinessWithBizID(ctx context.Context, bizID int) (retErr error) {
	logger.Debug("check the business: %d", bizID)

	//  Acquire the lock to ensuer the only one instance of the AM handles the bizID.
	mu, retErr := w.discoveryCli.CreateMutex(strconv.Itoa(bizID))
	if retErr != nil {
		return retErr
	}
	defer mu.Close()

	if retErr = mu.TryLock(ctx); retErr != nil {
		return retErr
	}

	defer func() {
		if retErr = mu.Unlock(ctx); retErr != nil {
			logger.Error("failed to unlock the biz: %d, errmsg: %v", bizID, retErr)
		}
	}()

	// Read all metadata by business ID.
	metaData, retErr := w.hadata.ReadMetadataCacheWithBizID(bizID, readBatchCount)
	if retErr != nil {
		return retErr
	}

	conds := []*storage.DbInstance{}
	metaInsts := map[string]*hamodel.DbmMetadata{}
	for _, meta := range metaData {
		conds = append(conds, &storage.DbInstance{
			BkCloudID: meta.BkCloudID,
			IP:        meta.IP,
			Port:      meta.Port,
		})

		metaInsts[fmt.Sprintf("%d:%s:%d", meta.BkCloudID, meta.IP, meta.Port)] = meta
	}

	// Read the status data reported by the probe.
	dbMetrics, err := w.hadata.ReadDbMetricsWithDbInstances(conds, -60*time.Second)
	if err != nil {
		// TODO: post notify by bk-monitor
	}

	dbEvents, err := w.hadata.ReadDbEventWithDbInstances(conds, -10*time.Minute)
	if err != nil {
		// TODO: post notify by bk-monitor
	}

	dbSkipInsts, err := w.hadata.ReadSkipDbInstancesWithBkBizID(bizID)
	if err != nil {
		// TODO: post notify by bk-monitor
	}

	skipInsts := map[string]*hamodel.SkipDbInstance{}
	for _, skipInst := range dbSkipInsts {
		skipInsts[fmt.Sprintf("%d:%s:%d", skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
	}

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkMissedProbeWithBizID(bizID, dbMetrics, skipInsts, metaInsts)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkEventWithBizID(bizID, dbEvents, skipInsts, metaInsts)
	}()

	// Parse and trigger switching logic.
	w.checkDbMetricWithBizID(ctx, bizID, dbMetrics)

	wg.Wait()
	return retErr
}

func (w *Workflow) scanEventWithoutMetadata() {
	events, err := w.hadata.ReadAllDbEventWithoutMetadata(readBatchCount, -10*time.Minute)
	if err != nil {
		logger.Warn("failed to read db event without metadata, errmsg: %s", err)
		return
	}

	for _, event := range events {
		monitorEvent := &monitor.EventData{
			Name:      event.Name.String(),
			Target:    event.Endpoint,
			Timestamp: uint64(event.UpdatedAt.UnixMilli()),
		}

		monitorEvent.Content.Content = fmt.Sprintf("without metadata, %s", event.Message)
		monitorEvent.Dimension.BkCloudID = event.BkCloudID
		monitorEvent.Dimension.IP = event.IP
		monitorEvent.Dimension.Port = event.Port
		monitorEvent.Dimension.DbTypeName = event.DbTypeName
		monitorEvent.Dimension.DbEventName = event.Name
		monitorEvent.Dimension.DbEventNameReason = event.Reason

		if err := monitor.PostBKMonitor(10*time.Second, monitorEvent); err != nil {
			logger.Warn("%v", err)
		}

		logger.Debug("check the business(event): %s %s", event.Endpoint, event.Message)
	}
}

func (w *Workflow) scanBusinesses(ctx context.Context) {
	bizIDs, err := w.hadata.GetBizIDs()
	if err != nil {
		logger.Warn("get business ids failed, %v", err)
		return
	}

	wgBizs := sync.WaitGroup{}
	for _, bizID := range bizIDs {
		wgBizs.Add(1)

		go func(bizID int) {
			defer wgBizs.Done()

			if err := w.checkBusinessWithBizID(ctx, bizID); err != nil {
				// TODO: notify admin
			}

		}(bizID)
	}

	wgBizs.Wait()
}

func (w *Workflow) Run(ctx context.Context) error {
	if w.cfg.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small,reset it to the default value(%v)",
			w.cfg.ScanInterval, scanIntervalLimitMin)

		w.cfg.ScanInterval = scanIntervalLimitMin
	}

	if err := w.dbmMetadata.Run(ctx); err != nil {
		logger.Error("failed to run the dbm metadata manager, errmsg: %v", err)
		return err
	}

	w.wg.Add(1)

	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(w.cfg.ScanInterval)
		defer timer.Stop()

		for {
			select {
			case <-w.quit:
				return

			case <-ctx.Done():
				return

			case <-timer.C:
				w.scanEventWithoutMetadata()
				w.scanBusinesses(ctx)
				timer.Reset(w.cfg.ScanInterval)
			}
		}
	}()

	return nil
}

func (w *Workflow) Close() {
	if w.quit != nil {
		close(w.quit)
	}

	w.wg.Wait()
	w.quit = nil
}
