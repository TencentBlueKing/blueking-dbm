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
	"dbm-services/common/dbha-v2/internal/analysis/detector"
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

// New create a workflow instance.
func New(cli *discovery.Client, db *hamysql.DB) (*Workflow, error) {
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

		discoveryCli: cli,
		quit:         make(chan struct{}, 1),
	}

	return wflow, nil
}

func key[T any](bkCloudId int, ip string, port T) string {
	return fmt.Sprintf("%d:%s:%v", bkCloudId, ip, port)
}

type Workflow struct {
	hadata       *storage.DbhaData
	dbmMetadata  *DbmMetadata
	discoveryCli *discovery.Client
	detector     detector.Detector
	switchers    map[haprobe.DbType]switcher.Switcher
	quit         chan struct{}
	wg           sync.WaitGroup
}

func (w *Workflow) Run(ctx context.Context) error {
	if config.Cfg.Workflow.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small,reset it to the default value(%v)",
			config.Cfg.Workflow.ScanInterval, scanIntervalLimitMin)

		config.Cfg.Workflow.ScanInterval = scanIntervalLimitMin
	}

	if err := w.dbmMetadata.Run(ctx); err != nil {
		logger.Error("failed to run the dbm metadata manager, errmsg: %v", err)
		return err
	}

	w.wg.Add(1)

	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(config.Cfg.Workflow.ScanInterval)
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
				timer.Reset(config.Cfg.Workflow.ScanInterval)
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

func (w *Workflow) databaseLivenessDoubleCheck(missedInsts []*hamodel.DbmMetadata) {
	// Trigger to execute the remote detect logic.
	if err := w.detector.Detect(missedInsts); err != nil {
		logger.Warn("failed to detect remote db-insts, errmsg: %s", err)
	}

	// Read the detected results.
	resps := w.detector.WaitResponses()

	// Post the alarm event by the bk-monitor.
	for _, resp := range resps {
		target := key(resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port)
		monitorEvent := &monitor.EventData{
			Name:      haprobe.DbEventNameProbeOffline.String(),
			Target:    target,
			Timestamp: uint64(time.Now().UnixMilli()),
		}

		if resp.Err != nil {
			monitorEvent.Content.Content = resp.Err.Error()
		} else {
			monitorEvent.Content.Content = string(resp.Data)
		}

		monitorEvent.Dimension.IP = resp.Meta.IP
		monitorEvent.Dimension.Port = resp.Meta.Port
		monitorEvent.Dimension.BkBizID = resp.Meta.BkBizID
		monitorEvent.Dimension.DbClusterType = resp.Meta.ClusterType
		monitorEvent.Dimension.DbMachineType = resp.Meta.MachineType
		monitorEvent.Dimension.DbEventName = resp.DbEventName
		monitorEvent.Dimension.DbEventNameReason = resp.DbEventNameReason

		if err := monitor.PostBKMonitor(10*time.Second, monitorEvent); err != nil {
			logger.Warn("%v", err)
		}
	}
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

	// Read the DB instance information reported by the probe.
	dbMetricKeys := map[string]struct{}{}
	for _, dbMetric := range dbMetrics {
		ips := strings.SplitSeq(dbMetric.IPs, constant.Delimiter)

		for ip := range ips {
			key := key(dbMetric.BkCloudID, ip, dbMetric.InstanceID)
			dbMetricKeys[key] = struct{}{}
		}
	}

	// Extract the instance of the DB that the probe is currently in an office state.
	missedProbeInsts := []*hamodel.DbmMetadata{}
	for _, dbMeta := range metaInsts {
		key := key(dbMeta.BkCloudID, dbMeta.IP, dbMeta.Port)

		if _, exists := skipDbInsts[key]; exists {
			logger.Info("skip the db instance: %s", key)
			continue
		}

		if _, exists := dbMetricKeys[key]; exists {
			continue
		}

		missedProbeInsts = append(missedProbeInsts, metaInsts[key])
	}

	// Trigger to recheck.
	w.databaseLivenessDoubleCheck(missedProbeInsts)
}

func (w *Workflow) checkDbMetricWithBizID(ctx context.Context, bizID int, dbMetrics []*hamodel.DatabaseMetric) {
	// TODO: Base on the metric data from the database, an in-depth analysis is conducted.
	//       If any abnormal events occur, the switching strategy will be triggered.
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

		metaInsts[key(meta.BkCloudID, meta.IP, meta.Port)] = meta
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
		skipInsts[key(skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
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
