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
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/workflow/parser"
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
	ErrReadMetadataFailure   = gerrors.Newf(gerrors.MysqlFailure, "failed to read metadata")
	ErrReadDbMetricFailure   = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB metrics")
	ErrReadDbEventFailure    = gerrors.Newf(gerrors.MysqlFailure, "failed to read DB event")
	ErrReadSkipDbInstFailure = gerrors.Newf(gerrors.MysqlFailure, "failed to read skip db-inst")
	ErrAcquireLockFailure    = gerrors.Newf(gerrors.EtcdFailure, "failed to acquire the lock for the business")
	ErrDetectorFailure       = gerrors.Newf(gerrors.Failure, "detector failure, switching is needed")
)

// Workflow represents the workflow engine for DBHA.
type Workflow struct {
	StatusParser

	hadata       *storage.DbhaData
	dbmSync      *Synchronizer
	discoveryCli *discovery.Client
	switchers    map[haprobe.DbType]switcher.Switcher
	quit         chan struct{}
	wg           sync.WaitGroup
}

// New create a workflow instance.
func New(cli *discovery.Client, db *hamysql.GormDB) (*Workflow, error) {
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

		discoveryCli: cli,
		quit:         make(chan struct{}, 1),
	}

	return wflow, nil
}

// Run run the workflow.
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
				w.scanBusinesses(ctx)
				logger.Debug("the workflow will scan the businesses, after: %v", config.Cfg.Workflow.ScanInterval)
				timer.Reset(config.Cfg.Workflow.ScanInterval)
			}
		}
	}()

	return nil
}

// Close close the workflow.
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
		resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port, content)

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

func (w *Workflow) processDetectorResponse(resp *detector.Response) error {
	if resp.Err == detector.ErrDetectorCreateSshConnection {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to dial the remote host with SSH, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		w.triggerAlarmWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		// NOTE: Trigger to switch the db.
		return ErrDetectorFailure
	}

	if resp.Err == detector.ErrDetectorCreateSshSession {
		resp.DbEventName = haprobe.DbEventNameDoubleCheckSshFailureV1
		resp.DbEventNameReason = haprobe.DbEventNameReasonConnectionException

		content := fmt.Sprintf("failed to create SSH session with the remote host, host: %d:%s:%d",
			resp.Meta.BkCloudID, resp.Meta.IP, config.Cfg.Detector.Ssh.Port)

		w.triggerAlarmWithDetectorResponse("", "", content, gerrors.Failure.Int(), resp)
		// NOTE: Trigger to switch the db.
		return ErrDetectorFailure
	}

	if resp.Err != nil {
		w.triggerAlarmWithDetectorResponse("", "", resp.Err.Error(), gerrors.Failure.Int(), resp)
		return nil
	}

	if resp.SshResp.ExitCode != 0 {
		content := fmt.Sprintf("%s, errmsg: %s", resp.SshResp.Data, resp.SshResp.ErrMsg)
		w.triggerAlarmWithDetectorResponse("", "", content, resp.SshResp.ExitCode, resp)
		return nil
	}

	// Parse the probe health.
	var health process.HealthInfo
	err := json.Unmarshal([]byte(resp.SshResp.Data), &health)
	if err != nil {
		w.triggerAlarmWithDetectorResponse("", "", err.Error(), gerrors.Failure.Int(), resp)
		return nil
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
	return nil
}

func (w *Workflow) databaseLivenessDoubleCheck(missedInsts []detector.DoubleCheckTask) {
	remoteDetector := detector.Detector{}

	// Trigger to execute the remote detect logic.
	if err := remoteDetector.Detect(missedInsts); err != nil {
		logger.Warn("failed to detect remote db-insts, errmsg: %s", err)
		return
	}

	// Read the detected results.
	resps := remoteDetector.WaitResponses()

	// Post the alarm event by the bk-monitor.
	// key: bkCloudId, value: map[dbType][]ip
	cloudIdIps := map[int]map[haprobe.DbType][]string{}

	for idx, resp := range resps {
		logger.Debug("idx: %d host: %s:%d resp: %p", idx, resp.Meta.IP, resp.Meta.Port, resp)
		err := w.processDetectorResponse(resp)
		if err == nil {
			continue
		}

		if err != ErrDetectorFailure {
			instId := key(resp.Meta.BkCloudID, resp.Meta.IP, resp.Meta.Port)
			logger.Warn("failed to process detector response, inst: %s, errmsg: %s", instId, err)
			continue
		}

		if _, ok := cloudIdIps[resp.Meta.BkCloudID]; ok {
			if cloudIdIps[resp.Meta.BkCloudID][resp.DbType] == nil {
				cloudIdIps[resp.Meta.BkCloudID][resp.DbType] = []string{}
			}

			cloudIdIps[resp.Meta.BkCloudID][resp.DbType] = append(cloudIdIps[resp.Meta.BkCloudID][resp.DbType], resp.Meta.IP)
			continue
		}

		cloudIdIps[resp.Meta.BkCloudID] = map[haprobe.DbType][]string{
			resp.DbType: {resp.Meta.IP},
		}
	}

	if len(cloudIdIps) == 0 {
		return
	}

	for cloudId, val := range cloudIdIps {
		for dbType, ips := range val {
			logger.Debug("cloudId: %d, dbType: %s, ips: %v", cloudId, dbType, ips)
			req := w.createSwitcherRequestWithIPs(cloudId, dbType, ips)
			if req == nil {
				continue
			}

			if !req.HasDbInstMetadata() {
				logger.Warn("no db inst metadata, dbType: %s, cloudId: %d, ips: %v", dbType, cloudId, ips)
				continue
			}

			logger.Debug("trigger switching, dbType: %s, cloudId: %d, ips: %v", dbType, cloudId, ips)
			w.triggerSwitching(dbType, req)
		}
	}
}

func (w *Workflow) createSwitcherRequestWithIPs(bkCloudId int, dbType haprobe.DbType, ips []string) *switcher.Request {
	metadatas, err := w.dbmSync.cli.QueryMetadataFromDbm(context.Background(), bkCloudId, ips)

	if err != nil {
		if errors.Is(err, dbm.ErrNoResponse) {
			return nil
		}

		logger.Warn("failed to query metadata from DBM, bkCloudId: %d, ips: %v, errmsg: %s", bkCloudId, ips, err)
		return nil
	}

	req := &switcher.Request{DbType: dbType}
	for _, meta := range metadatas {
		if meta.Status == dbm.Unavailable {
			logger.Info("the database instance is unavailable, skipping, inst: %s", key(meta.BkCloudID, meta.IP, meta.Port))
			continue
		}

		req.AddDbInstMetadata((*switcher.MysqlInstanceMetadata)(meta))
	}

	return req
}

func (w *Workflow) triggerSwitching(dbType haprobe.DbType, req *switcher.Request) {
	if !config.Cfg.Workflow.EnableSwitching {
		logger.Warn("switching operation is disabled")
		return
	}

	sw, exists := w.switchers[dbType]
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
		instKey := switcher.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)

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

func (w *Workflow) checkEventWithBizId(bizId int, dbEvents []*haprobe.DbEvent,
	skipDbInsts map[string]*hamodel.SkipDbInstance, metaInsts map[string]*hamodel.DbmMetadata) {

	// TODO: read switching strategy with bizId
	_ = bizId

	badInsts := []detector.DoubleCheckTask{}

	for _, event := range dbEvents {
		key := key(event.BkCloudID, event.Endpoint.Host, event.Endpoint.Port)

		if _, exists := skipDbInsts[key]; exists {
			logger.Info("skip the db-inst: %s", key)
			continue
		}

		meta, exists := metaInsts[key]
		if !exists {
			logger.Warn("not found the meta for the db-inst: %s", key)
			continue
		}

		logger.Warn("recheck the db-inst: %s", key)
		badInsts = append(badInsts, detector.DoubleCheckTask{
			Meta:   meta,
			DbType: event.DbTypeName,
		})
	}

	// Trigger to recheck.
	w.databaseLivenessDoubleCheck(badInsts)
}

func (w *Workflow) checkDbHosts(dbHosts []*haprobe.HostMetric, checkDbEventsFunc func(dbEvents []*haprobe.DbEvent)) {
	dbEvents, err := w.ParseHostStatus(dbHosts)
	if err != nil {
		logger.Warn("failed to parse the host status, errmsg: %s", err)
		return
	}

	if len(dbEvents) == 0 {
		return
	}

	checkDbEventsFunc(dbEvents)
}

func (w *Workflow) checkDbStatus(dbStatusVals []parser.DBTyperWrapper,
	checkDbEventsFunc func(dbEvents []*haprobe.DbEvent)) {

	dbEvents, err := w.ParseDbStatus(dbStatusVals)
	if err != nil {
		logger.Warn("failed to parse the DB status, errmsg: %s", err)
		return
	}

	checkDbEventsFunc(dbEvents)
}

func (w *Workflow) checkMissedProbe(dbStatus []*hamodel.DbhaDataStatus, skipDbInsts map[string]*hamodel.SkipDbInstance,
	metaInsts map[string]*hamodel.DbmMetadata) {

	dbMetricKeys := map[string]struct{}{}
	for _, dbStat := range dbStatus {
		key := key(dbStat.BkCloudID, dbStat.DbIp, dbStat.DbPort)
		dbMetricKeys[key] = struct{}{}
	}

	// Extract the instance of the DB that the probe is currently in an office state.
	missedProbeInsts := []detector.DoubleCheckTask{}
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

		logger.Debug("missed probe instances: %#v", *dbMeta)
		missedProbeInsts = append(missedProbeInsts, detector.DoubleCheckTask{
			Meta:   dbMeta,
			DbType: dbMeta.GetDbType(),
		})
	}

	// Trigger to recheck.
	w.databaseLivenessDoubleCheck(missedProbeInsts)
}

// acquireBusinessLock acquires and locks the mutex for a business.
// It returns the mutex and a cleanup function that should be deferred.
func (w *Workflow) acquireBusinessLock(ctx context.Context, bizId int) (discovery.ConcurrencyMutex, func(), error) {
	mu, err := w.discoveryCli.CreateMutex(strconv.Itoa(bizId))
	if err != nil {
		logger.Warn("failed to acquire the mutex lock for the business, bizId: %d, errmsg: %s", bizId, err)
		return nil, nil, ErrAcquireLockFailure
	}

	if err := mu.TryLock(ctx); err != nil {
		mu.Close()
		logger.Warn("failed to lock the business, bizId: %d, errmsg: %s", bizId, err)
		return nil, nil, err
	}

	cleanup := func() {
		if err := mu.Unlock(ctx); err != nil {
			logger.Warn("failed to unlock the biz: %d, errmsg: %v", bizId, err)
		}
		mu.Close()
	}

	return mu, cleanup, nil
}

// businessMetadata contains metadata and conditions for a business.
type businessMetadata struct {
	metaInsts map[string]*hamodel.DbmMetadata
	conds     []*storage.DbInstance
}

// readBusinessMetadata reads all metadata for a business and builds the conditions.
func (w *Workflow) readBusinessMetadata(bizId int) (*businessMetadata, error) {
	metaData, err := w.hadata.ReadMetadataCacheWithBizID(bizId, readBatchCount,
		config.Cfg.Workflow.ReadDbMetaOffsetDuration)
	if err != nil {
		logger.Warn("failed to read the DB metadata for the business, bizId: %d, errmsg: %s", bizId, err)
		return nil, ErrReadMetadataFailure
	}

	conds := make([]*storage.DbInstance, 0, len(metaData))
	metaInsts := make(map[string]*hamodel.DbmMetadata, len(metaData))

	for _, meta := range metaData {
		conds = append(conds, &storage.DbInstance{
			BkCloudID: meta.BkCloudID,
			IP:        meta.IP,
			Port:      meta.Port,
		})
		metaInsts[key(meta.BkCloudID, meta.IP, meta.Port)] = meta
	}

	return &businessMetadata{
		metaInsts: metaInsts,
		conds:     conds,
	}, nil
}

// dbStatusData contains extracted data from database status.
type dbStatusData struct {
	dbEvents     []*haprobe.DbEvent
	dbHosts      []*haprobe.HostMetric
	dbStatusVals []parser.DBTyperWrapper
}

// extractDbStatusData extracts events, hosts, and status values from database status.
func (w *Workflow) extractDbStatusData(dbStatus []*hamodel.DbhaDataStatus) *dbStatusData {
	data := &dbStatusData{
		dbEvents:     make([]*haprobe.DbEvent, 0),
		dbHosts:      make([]*haprobe.HostMetric, 0),
		dbStatusVals: make([]parser.DBTyperWrapper, 0),
	}

	for _, dbStat := range dbStatus {
		if dbStat.Events.Valid {
			data.dbEvents = append(data.dbEvents, dbStat.Events.Data...)
		}

		if dbStat.Host.Valid {
			data.dbHosts = append(data.dbHosts, dbStat.Host.Data)
		}

		if dbStat.Value.Valid {
			data.dbStatusVals = append(data.dbStatusVals, parser.DBTyperWrapper{
				DbTypeName: dbStat.DbTypeName,
				Value:      dbStat.Value.Data,
			})
		}
	}

	return data
}

// readBusinessSkipInstances reads skipped instances for a business.
func (w *Workflow) readBusinessSkipInstances(bizId int) (map[string]*hamodel.SkipDbInstance, error) {
	dbSkipInsts, err := w.hadata.ReadSkipDbInstancesWithBkBizId(bizId)
	if err != nil {
		logger.Warn("failed to read the skipped DB insts for the business: %d, errmsg: %s", bizId, err)
		return nil, ErrReadSkipDbInstFailure
	}

	skipInsts := make(map[string]*hamodel.SkipDbInstance, len(dbSkipInsts))
	for _, skipInst := range dbSkipInsts {
		skipInsts[key(skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
	}

	return skipInsts, nil
}

// runBusinessChecks runs all check tasks concurrently for a business.
func (w *Workflow) runBusinessChecks(
	bizId int,
	dbStatus []*hamodel.DbhaDataStatus,
	statusData *dbStatusData,
	skipInsts map[string]*hamodel.SkipDbInstance,
	metaInsts map[string]*hamodel.DbmMetadata,
) {
	checkDbEventFunc := func(dbEvents []*haprobe.DbEvent) {
		w.checkEventWithBizId(bizId, dbEvents, skipInsts, metaInsts)
	}

	var wg sync.WaitGroup

	// Check missed probe instances
	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkMissedProbe(dbStatus, skipInsts, metaInsts)
	}()

	// Check database events
	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkEventWithBizId(bizId, statusData.dbEvents, skipInsts, metaInsts)
	}()

	// Check database hosts
	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkDbHosts(statusData.dbHosts, checkDbEventFunc)
	}()

	// Check database status
	wg.Add(1)
	go func() {
		defer wg.Done()
		w.checkDbStatus(statusData.dbStatusVals, checkDbEventFunc)
	}()

	wg.Wait()
}

// checkBusinessWithBizID checks a business by its ID.
// It acquires a lock, reads metadata and status, then runs various checks concurrently.
func (w *Workflow) checkBusinessWithBizID(ctx context.Context, bizId int) error {
	logger.Debug("check the business: %d", bizId)

	// Acquire the lock to ensure only one instance of the AM handles the bizID.
	_, unlock, err := w.acquireBusinessLock(ctx, bizId)
	if err != nil {
		return err
	}
	defer unlock()

	// Read business metadata
	bizMeta, err := w.readBusinessMetadata(bizId)
	if err != nil {
		return err
	}

	// Read the status data reported by the probe
	dbStatus, err := w.hadata.ReadDbStatusWithDbInstances(bizMeta.conds, config.Cfg.Workflow.ReadDbMetricOffsetDuration)
	if err != nil {
		logger.Warn("failed to read the DB status with the conditions: %v, bizId: %d, errmsg: %s", bizMeta.conds, bizId, err)
		return ErrReadDbMetricFailure
	}

	// Extract data from database status
	statusData := w.extractDbStatusData(dbStatus)

	// Read skipped instances
	skipInsts, err := w.readBusinessSkipInstances(bizId)
	if err != nil {
		return err
	}

	// Run all checks concurrently
	w.runBusinessChecks(bizId, dbStatus, statusData, skipInsts, bizMeta.metaInsts)

	logger.Debug("finished checking the business: %d", bizId)
	return nil
}

func (w *Workflow) scanBusinesses(ctx context.Context) {
	bizIDs, err := w.hadata.GetBizIDs()
	if err != nil {
		logger.Warn("failed to get business IDs, errmsg: %s", err)
		return
	}

	wg := sync.WaitGroup{}
	sem := make(chan struct{}, 10) // 10 is the max concurrent business checks

	for _, bizID := range bizIDs {
		sem <- struct{}{} // acquire the semaphore
		wg.Add(1)

		go func(bizId int) {
			defer wg.Done()
			defer func() { <-sem }() // release the semaphore

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

	wg.Wait()
}

func key[T any](bkCloudId int, ip string, port T) string {
	return fmt.Sprintf("%d:%s:%v", bkCloudId, ip, port)
}
