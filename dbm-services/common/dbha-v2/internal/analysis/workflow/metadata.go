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
	"strconv"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/workflow/parser"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// MetadataReader reads business metadata, skip instances, and DB status data; it also acquires business locks.
type MetadataReader struct {
	hadata       *storage.DbhaData
	discoveryCli *discovery.Client
}

// NewMetadataReader creates a MetadataReader.
func NewMetadataReader(hadata *storage.DbhaData, discoveryCli *discovery.Client) *MetadataReader {
	return &MetadataReader{hadata: hadata, discoveryCli: discoveryCli}
}

// BusinessMetadata contains metadata and conditions for a business.
type BusinessMetadata struct {
	MetaInsts map[string]*hamodel.DbmMetadata
	Conds     []*storage.DbInstance
}

// ReadBusinessMetadata reads all metadata for a business and builds the conditions.
func (r *MetadataReader) ReadBusinessMetadata(bizId int) (*BusinessMetadata, error) {
	metaData, err := r.hadata.ReadMetadataCacheWithBizID(bizId, readBatchCount,
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
		metaInsts[instanceKey(meta.BkCloudID, meta.IP, meta.Port)] = meta
	}

	return &BusinessMetadata{
		MetaInsts: metaInsts,
		Conds:     conds,
	}, nil
}

// ReadBusinessSkipInstances reads skipped instances for a business.
func (r *MetadataReader) ReadBusinessSkipInstances(bizId int) (map[string]*hamodel.SkipDbInstance, error) {
	dbSkipInsts, err := r.hadata.ReadSkipDbInstancesWithBkBizId(bizId)
	if err != nil {
		logger.Warn("failed to read the skipped DB insts for the business: %d, errmsg: %s", bizId, err)
		return nil, ErrReadSkipDbInstFailure
	}

	skipInsts := make(map[string]*hamodel.SkipDbInstance, len(dbSkipInsts))
	for _, skipInst := range dbSkipInsts {
		skipInsts[instanceKey(skipInst.BkCloudID, skipInst.InstanceIP, skipInst.InstancePort)] = skipInst
	}

	return skipInsts, nil
}

// AcquireBusinessLock acquires and locks the mutex for a business.
// It returns the mutex and a cleanup function that should be deferred.
func (r *MetadataReader) AcquireBusinessLock(ctx context.Context, bizId int) (discovery.ConcurrencyMutex, func(), error) {
	mu, err := r.discoveryCli.CreateMutex(strconv.Itoa(bizId))
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
