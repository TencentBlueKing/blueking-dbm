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
	"encoding/json"
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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	scanIntervalLimitMin = 5 * time.Second
	readBatchCount       = 1000
)

var (
	ErrCreateMutexFailure    = gerrors.Newf(gerrors.EtcdFailure, "failed to create a mutex for a business")
	ErrReadeMetadataFailure  = gerrors.Newf(gerrors.MysqlFailure, "failed to read metadata")
	ErrReadDbMetricFailure   = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB metrics")
	ErrReadDbEventFailure    = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB event")
	ErrReadSkipDbInstFailure = gerrors.Newf(gerrors.MysqlFailure, "failed to read skip db-inst")
	ErrAcquireLockFailure    = gerrors.Newf(gerrors.EtcdFailure, "failed to acquire the lock for the business")
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

type Workflow struct {
	hadata       *storage.DbhaData
	dbmMetadata  *DbmMetadata
	discoveryCli *discovery.Client
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

func (w *Workflow) triggerAlarmWithDetectorResponse(procName string, status process.Status,
	content string, exitCode int, resp *detector.Response) {

	target := key(resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port)
	monitorEvent := &monitor.EventData{
		Name:      resp.DbEventName.String(),
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}

	monitorEvent.Content.Content = content

	monitorEvent.Dimension.DetectorExitCode = exitCode
	monitorEvent.Dimension.IP = resp.Meta.IP
	monitorEvent.Dimension.Port = resp.Meta.Port
	monitorEvent.Dimension.BkBizId = resp.Meta.BkBizID
	monitorEvent.Dimension.DbClusterType = resp.Meta.ClusterType
	monitorEvent.Dimension.DbMachineType = resp.Meta.MachineType
	monitorEvent.Dimension.DetectorProcName = procName
	monitorEvent.Dimension.DetectorProcStatus = status
	monitorEvent.Dimension.DbEventName = resp.DbEventName
	monitorEvent.Dimension.DbEventNameReason = resp.DbEventNameReason.Str()

	logger.Info("the workflow triggers an alarm, db-inst: %d:%s:%d content: %s",
		resp.Meta.BkBizID, resp.Meta.IP, resp.Meta.Port, content)

	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		logger.Warn("failed to post the alarm event to BkMonitor, errmsg: %s", err)
	}
}

func (w *Workflow) triggerAlarmWithBizId(bizId int, content string) {
	target := fmt.Sprintf("BizId: %d", bizId)

	monitorEvent := &monitor.EventData{
		Name:      "",
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}

	monitorEvent.Content.Content = content

	monitorEvent.Dimension.BkBizId = bizId

	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		logger.Warn("%s", err)
	}

}

func (w *Workflow) processDetectorResponse(resp *detector.Response) {
	if resp.Err == detector.ErrDetectorCreateSshConnection {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to dial the remote host with SSH, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		w.triggerAlarmWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		// TODO: Trigger to switch the db.
		return
	}

	if resp.Err == detector.ErrDetectorCreateSshSession {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to create SSH session with the remote host, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		w.triggerAlarmWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		// TODO: Trigger to switch the db.
		return
	}

	if resp.Err != nil {
		w.triggerAlarmWithDetectorResponse("", "", resp.Err.Error(), gerrors.Failure.Int(), resp)
		return
	}

	if resp.SshResp.ExitCode != 0 {
		content := fmt.Sprintf("%s, errmsg: %s", resp.SshResp.Data, resp.SshResp.ErrMsg)
		w.triggerAlarmWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return
	}

	// Parse the probe health.
	var health process.HealthInfo
	err := json.Unmarshal([]byte(resp.SshResp.Data), &health)
	if err != nil {
		w.triggerAlarmWithDetectorResponse("", "", err.Error(), gerrors.Failure.Int(), resp)
		return
	}

	content := fmt.Sprintf("pid: %d proc name: %s status: %s", health.Pid, health.ProcName, health.Status)
	if health.Pid == process.InvalidPid {
		content = health.ErrMsg
	} else {
		// Probe is running, but there are no target database metrics.
		content = fmt.Sprintf("%s, db: %s:%d", content, resp.Meta.IP, resp.Meta.Port)
		resp.DbEventName = haprobe.DbEventNameDetectFailure
		resp.DbEventNameReason = haprobe.DbEventNameReasonNoTarget
	}

	w.triggerAlarmWithDetectorResponse(health.ProcName, health.Status, content, resp.SshResp.ExitCode, resp)
}

func (w *Workflow) databaseLivenessDoubleCheck(missedInsts []*hamodel.DbmMetadata) {
	remoteDetector := detector.Detector{}

	// Trigger to execute the remote detect logic.
	if err := remoteDetector.Detect(missedInsts); err != nil {
		logger.Warn("failed to detect remote db-insts, errmsg: %s", err)
		return
	}

	// Read the detected results.
	resps := remoteDetector.WaitResponses()

	// Post the alarm event by the bk-monitor.
	for idx, resp := range resps {
		logger.Debug("idx: %d host: %s:%d resp: %p", idx, resp.Meta.IP, resp.Meta.Port, resp)
		w.processDetectorResponse(resp)
	}
}

func (w *Workflow) checkEventWithBizId(bizId int, dbEvents []*hamodel.DbEvent,
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
	req.BkBizID = bizId
	req.BreakdownEvents = events
	req.MetaInsts = metas

	w.switchers[haprobe.DbTypeMysql].Switch(context.Background(), req)
}

func (w *Workflow) checkMissedProbe(dbMetrics []*hamodel.DatabaseMetric,
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
			logger.Debug("db instance(%s) has probe", key)
			continue
		}

		missedProbeInsts = append(missedProbeInsts, metaInsts[key])
	}

	// Trigger to recheck.
	w.databaseLivenessDoubleCheck(missedProbeInsts)
}

func (w *Workflow) checkDbMetricWithBizId(ctx context.Context, bizId int, dbMetrics []*hamodel.DatabaseMetric) {
	// TODO: Base on the metric data from the database, an in-depth analysis is conducted.
	//       If any abnormal events occur, the switching strategy will be triggered.
}

func (w *Workflow) checkBusinessWithBizID(ctx context.Context, bizId int) (retErr error) {
	logger.Debug("check the business: %d", bizId)

	//  Acquire the lock to ensuer the only one instance of the AM handles the bizID.
	mu, retErr := w.discoveryCli.CreateMutex(strconv.Itoa(bizId))
	if retErr != nil {
		logger.Warn("failed to acquire the mutex lock for the business, bizId: %d, errmsg: %s", bizId, retErr)
		return ErrAcquireLockFailure
	}

	defer mu.Close()

	if retErr = mu.TryLock(ctx); retErr != nil {
		logger.Warn("failed to lock the business, bizId: %d, errmsg: %s", bizId, retErr)
		return retErr
	}

	defer func() {
		if retErr = mu.Unlock(ctx); retErr != nil {
			logger.Warn("failed to unlock the biz: %d, errmsg: %v", bizId, retErr)
		}
	}()

	// Read all metadata by business ID.
	metaData, retErr := w.hadata.ReadMetadataCacheWithBizID(bizId, readBatchCount,
		config.Cfg.Workflow.ReadDbMetaOffsetDuration)

	if retErr != nil {
		logger.Warn("failed to read the DB metadata for the business, bizId: %d, errmsg: %s", bizId, retErr)
		return ErrReadeMetadataFailure
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
	dbMetrics, err := w.hadata.ReadDbMetricsWithDbInstances(conds, config.Cfg.Workflow.ReadDbMetricOffsetDuration)
	if err != nil {
		logger.Warn("failed to read the DB metrics with the conditions: %v, bizId: %d, errmsg: %s", conds, bizId, err)
		return ErrReadDbMetricFailure
	}

	dbEvents, err := w.hadata.ReadDbEventWithDbInstances(conds, config.Cfg.Workflow.ReadDbEventOffsetDuration)
	if err != nil {
		logger.Warn("failed to read the DB events with the conditions: %v, bizId: %d, errmsg: %s", conds, bizId, err)
		return ErrReadDbEventFailure
	}

	dbSkipInsts, err := w.hadata.ReadSkipDbInstancesWithBkBizId(bizId)
	if err != nil {
		logger.Warn("failed to read the skipped DB insts for the business: %d, errmsg: %s", bizId, err)
		return ErrReadSkipDbInstFailure
	}

	skipInsts := map[string]*hamodel.SkipDbInstance{}
	for _, skipInst := range dbSkipInsts {
		skipInsts[key(skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
	}

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkMissedProbe(dbMetrics, skipInsts, metaInsts)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkEventWithBizId(bizId, dbEvents, skipInsts, metaInsts)
	}()

	// Parse and trigger switching logic.
	w.checkDbMetricWithBizId(ctx, bizId, dbMetrics)

	wg.Wait()
	return retErr
}

func (w *Workflow) scanEventWithoutMetadata() {
	events, err := w.hadata.ReadAllDbEventWithoutMetadata(readBatchCount, config.Cfg.Workflow.ReadDbEventOffsetDuration)
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
		monitorEvent.Dimension.BkCloudId = event.BkCloudID
		monitorEvent.Dimension.IP = event.IP
		monitorEvent.Dimension.Port = event.Port
		monitorEvent.Dimension.DbTypeName = event.DbTypeName
		monitorEvent.Dimension.DbEventName = event.Name
		monitorEvent.Dimension.DbEventNameReason = event.Reason.Str()

		if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
			logger.Warn("failed to post an alarm to the BkMonitor, errmsg: %s", err)
		}

		logger.Debug("check the business(event): %s %s", event.Endpoint, event.Message)
	}
}

func (w *Workflow) scanBusinesses(ctx context.Context) {
	bizIDs, err := w.hadata.GetBizIDs()
	if err != nil {
		logger.Warn("failed to get business IDs, errmsg: %s", err)
		return
	}

	wgBizs := sync.WaitGroup{}
	for _, bizID := range bizIDs {
		wgBizs.Add(1)

		go func(bizId int) {
			defer wgBizs.Done()

			err := w.checkBusinessWithBizID(ctx, bizId)
			if err == nil {
				logger.Info("successfully complete the business check, bizId: %d", bizId)
				return
			}

			// Trigger an alarm and send it to the monitoring platform.
			logger.Warn("failed to check the business, bizId: %d", bizId)
			w.triggerAlarmWithBizId(bizId, err.Error())

		}(bizID)
	}

	wgBizs.Wait()
}

func key[T any](bkCloudId int, ip string, port T) string {
	return fmt.Sprintf("%d:%s:%v", bkCloudId, ip, port)
}
