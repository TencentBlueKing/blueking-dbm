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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/parser"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// MetadataReader reads business metadata, skip instances, and DB status data; it also acquires business locks.
type MetadataReader struct {
	hadata       *storage.DbhaData
	discoveryCli *discovery.Client
	myServiceID  string
}

// NewMetadataReader creates a MetadataReader.
func NewMetadataReader(hadata *storage.DbhaData, discoveryCli *discovery.Client, serviceID string) *MetadataReader {
	return &MetadataReader{hadata: hadata, discoveryCli: discoveryCli, myServiceID: serviceID}
}

// BusinessMetadata contains metadata and conditions for a business.
type BusinessMetadata struct {
	MetaInsts map[string]*hamodel.DbmMetadata
	Conds     []*storage.DbInstance
}

// ReadBusinessMetadata reads all metadata for a business and builds the conditions.
func (r *MetadataReader) ReadBusinessMetadata(bizId int) (*BusinessMetadata, error) {
	start := time.Now()
	metaData, err := r.hadata.ReadMetadataCacheWithBizID(bizId, readBatchCount,
		config.Cfg.Workflow.ReadDbMetaOffsetDuration)
	if err != nil {
		logger.Warn("failed to read the DB metadata for the business, bizId: %d, errmsg: %s", bizId, err)
		r.reportDbQueryError(apm.MetricQueryTypeReadMetadata)
		return nil, ErrReadMetadataFailure
	}
	r.reportDbQueryTime(apm.MetricQueryTypeReadMetadata, start)

	conds := make([]*storage.DbInstance, 0, len(metaData))
	metaInsts := make(map[string]*hamodel.DbmMetadata, len(metaData))

	for _, meta := range metaData {
		conds = append(conds, &storage.DbInstance{
			BkCloudID: meta.BkCloudID,
			IP:        meta.IP,
			Port:      meta.Port,
		})
		metaInsts[instanceKey(meta.BkCloudID, meta.IP, meta.Port)] = meta
	}

	return &BusinessMetadata{
		MetaInsts: metaInsts,
		Conds:     conds,
	}, nil
}

// ReadBusinessSkipInstances reads skipped instances for a business.
func (r *MetadataReader) ReadBusinessSkipInstances(bizId int) (map[string]*hamodel.SkipDbInstance, error) {
	start := time.Now()
	dbSkipInsts, err := r.hadata.ReadSkipDbInstancesWithBkBizId(bizId)
	if err != nil {
		logger.Warn("failed to read the skipped DB insts for the business: %d, errmsg: %s", bizId, err)
		r.reportDbQueryError(apm.MetricQueryTypeReadSkipInstances)
		return nil, ErrReadSkipDbInstFailure
	}
	r.reportDbQueryTime(apm.MetricQueryTypeReadSkipInstances, start)

	skipInsts := make(map[string]*hamodel.SkipDbInstance, len(dbSkipInsts))
	for _, skipInst := range dbSkipInsts {
		skipInsts[instanceKey(skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
	}

	return skipInsts, nil
}

// ReadDbStatusWithInstances reads DB status for the given instances and reports DB query metrics.
func (r *MetadataReader) ReadDbStatusWithInstances(conds []*storage.DbInstance,
	offsetDuration time.Duration) ([]*hamodel.DbhaDataStatus, error) {

	start := time.Now()
	dbStatus, err := r.hadata.ReadDbStatusWithDbInstances(conds, offsetDuration)
	if err != nil {
		r.reportDbQueryError(apm.MetricQueryTypeReadDBStatus)
		return nil, err
	}
	r.reportDbQueryTime(apm.MetricQueryTypeReadDBStatus, start)

	return dbStatus, nil
}

// reportDbQueryTime reports DB query time consuming metric.
func (r *MetadataReader) reportDbQueryTime(queryType string, start time.Time) {
	if reportErr := apm.DbQueryTimeConsumingMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelQueryType:     queryType,
		haapm.MetricLabelServiceID:   r.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(time.Since(start).Milliseconds())); reportErr != nil {
		logger.Warn("failed to report db query time consuming metric, queryType: %s, errmsg: %s", queryType, reportErr)
	}
}

// reportDbQueryError reports DB query error metric.
func (r *MetadataReader) reportDbQueryError(queryType string) {
	if reportErr := apm.DbQueryErrorTotal.IncWithLabels(map[string]string{
		apm.MetricLabelQueryType:     queryType,
		haapm.MetricLabelServiceID:   r.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}); reportErr != nil {
		logger.Warn("failed to report db query error metric, queryType: %s, errmsg: %s", queryType, reportErr)
	}
}

// AcquireScanLock acquires the scan lock for a business.
// It prevents multiple AM instances from scanning the same business simultaneously.
// Returns the mutex and a cleanup function that should be deferred.
func (r *MetadataReader) AcquireScanLock(ctx context.Context, bizId int) (discovery.ConcurrencyMutex, func(), error) {
	return r.acquireLock(ctx, "scan", bizId)
}

// AcquireSwitchLock acquires the switch lock for a business.
// It prevents multiple AM instances from executing switching for the same business simultaneously.
// SwitchLock is independent of ScanLock — scanning and switching do not block each other.
// Returns the mutex and a cleanup function that should be deferred.
func (r *MetadataReader) AcquireSwitchLock(ctx context.Context, bizId int) (discovery.ConcurrencyMutex, func(), error) {
	return r.acquireLock(ctx, "switch", bizId)
}

// acquireLock acquires a distributed lock with the given prefix and business ID.
func (r *MetadataReader) acquireLock(ctx context.Context, prefix string, bizId int) (discovery.ConcurrencyMutex, func(), error) {
	key := fmt.Sprintf("%s:%d", prefix, bizId)
	mu, err := r.discoveryCli.CreateMutex(key)
	if err != nil {
		logger.Warn("failed to create %s mutex for the business, bizId: %d, errmsg: %s", prefix, bizId, err)
		return nil, nil, ErrAcquireLockFailure
	}

	if err := mu.TryLock(ctx); err != nil {
		mu.Close()
		logger.Warn("failed to acquire %s lock for the business, bizId: %d, errmsg: %s", prefix, bizId, err)
		return nil, nil, err
	}

	cleanup := func() {
		if err := mu.Unlock(ctx); err != nil {
			logger.Warn("failed to unlock %s lock for biz: %d, errmsg: %s", prefix, bizId, err)
		}
		mu.Close()
	}

	return mu, cleanup, nil
}

// DbStatusData contains extracted data from database status.
type DbStatusData struct {
	DbEvents     []*haprobe.DbEvent
	DbHosts      []*haprobe.HostMetric
	DbStatusVals []parser.DBTyperWrapper
}

// ExtractDbStatusData extracts events, hosts, and status values from database status.
func (r *MetadataReader) ExtractDbStatusData(dbStatus []*hamodel.DbhaDataStatus) *DbStatusData {
	data := &DbStatusData{
		DbEvents:     make([]*haprobe.DbEvent, 0),
		DbHosts:      make([]*haprobe.HostMetric, 0),
		DbStatusVals: make([]parser.DBTyperWrapper, 0),
	}

	for _, dbStat := range dbStatus {
		if dbStat.Events.Valid {
			data.DbEvents = append(data.DbEvents, dbStat.Events.Data...)
		}

		if dbStat.Host.Valid {
			data.DbHosts = append(data.DbHosts, dbStat.Host.Data)
		}

		if dbStat.Value.Valid {
			data.DbStatusVals = append(data.DbStatusVals, parser.DBTyperWrapper{
				DbTypeName: dbStat.DbTypeName,
				Value:      dbStat.Value.Data,
			})
		}
	}

	return data
}
