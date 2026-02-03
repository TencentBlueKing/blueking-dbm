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
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/detector"
	"dbm-services/common/dbha-v2/internal/analysis/workflow/parser"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// BusinessChecker runs event, host, status, and missed-probe checks for a business and triggers detector/switch via DetectorHandler.
type BusinessChecker struct {
	parser   *StatusParser
	detector *DetectorHandler
}

// NewBusinessChecker creates a BusinessChecker.
func NewBusinessChecker(parser *StatusParser, detector *DetectorHandler) *BusinessChecker {
	return &BusinessChecker{parser: parser, detector: detector}
}

// CheckEventWithBizId builds double-check tasks from dbEvents and runs liveness double-check.
func (c *BusinessChecker) CheckEventWithBizId(bizId int, dbEvents []*haprobe.DbEvent,
	skipDbInsts map[string]*hamodel.SkipDbInstance, metaInsts map[string]*hamodel.DbmMetadata) {
	_ = bizId

	badInsts := []detector.DoubleCheckTask{}

	for _, event := range dbEvents {
		key := instanceKey(event.BkCloudID, event.Endpoint.Host, event.Endpoint.Port)

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

	c.detector.LivenessDoubleCheck(badInsts)
}

// CheckDbHosts parses host status and invokes checkDbEventsFunc with the resulting events.
func (c *BusinessChecker) CheckDbHosts(dbHosts []*haprobe.HostMetric, checkDbEventsFunc func(dbEvents []*haprobe.DbEvent)) {
	dbEvents, err := c.parser.ParseHostStatus(dbHosts)
	if err != nil {
		logger.Warn("failed to parse the host status, errmsg: %s", err)
		return
	}

	if len(dbEvents) == 0 {
		return
	}

	checkDbEventsFunc(dbEvents)
}

// CheckDbStatus parses DB status and invokes checkDbEventsFunc with the resulting events.
func (c *BusinessChecker) CheckDbStatus(dbStatusVals []parser.DBTyperWrapper,
	checkDbEventsFunc func(dbEvents []*haprobe.DbEvent)) {
	dbEvents, err := c.parser.ParseDbStatus(dbStatusVals)
	if err != nil {
		logger.Warn("failed to parse the DB status, errmsg: %s", err)
		return
	}

	checkDbEventsFunc(dbEvents)
}

// CheckMissedProbe finds instances with no probe and runs liveness double check.
func (c *BusinessChecker) CheckMissedProbe(dbStatus []*hamodel.DbhaDataStatus, skipDbInsts map[string]*hamodel.SkipDbInstance,
	metaInsts map[string]*hamodel.DbmMetadata) {
	dbMetricKeys := map[string]struct{}{}
	for _, dbStat := range dbStatus {
		key := instanceKey(dbStat.BkCloudID, dbStat.DbIp, dbStat.DbPort)
		dbMetricKeys[key] = struct{}{}
	}

	missedProbeInsts := []detector.DoubleCheckTask{}
	for _, dbMeta := range metaInsts {
		key := instanceKey(dbMeta.BkCloudID, dbMeta.IP, dbMeta.Port)

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

	c.detector.LivenessDoubleCheck(missedProbeInsts)
}

// RunBusinessChecks runs all check tasks concurrently for a business.
func (c *BusinessChecker) RunBusinessChecks(
	bizId int,
	dbStatus []*hamodel.DbhaDataStatus,
	statusData *DbStatusData,
	skipInsts map[string]*hamodel.SkipDbInstance,
	metaInsts map[string]*hamodel.DbmMetadata,
) {
	checkDbEventFunc := func(dbEvents []*haprobe.DbEvent) {
		c.CheckEventWithBizId(bizId, dbEvents, skipInsts, metaInsts)
	}

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		c.CheckMissedProbe(dbStatus, skipInsts, metaInsts)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		c.CheckEventWithBizId(bizId, statusData.DbEvents, skipInsts, metaInsts)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		c.CheckDbHosts(statusData.DbHosts, checkDbEventFunc)
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		c.CheckDbStatus(statusData.DbStatusVals, checkDbEventFunc)
	}()

	wg.Wait()
}
