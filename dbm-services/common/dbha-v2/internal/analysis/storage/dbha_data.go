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

package storage

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// DbInstance represents a database instance identified by cloud ID, IP, and port.
type DbInstance struct {
	BkCloudID int
	IP        string
	Port      int
}

// DbhaData provides data access methods for DBHA analysis, backed by a GORM database connection.
type DbhaData struct {
	DB *hamysql.GormDB
}

// GetBizIDs returns all distinct business IDs from DBM metadata.
func (ha *DbhaData) GetBizIDs(ctx context.Context) ([]int, error) {
	bkBizIDs := []int{}

	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbmMetadata{}).
		Select(hamodel.DbmMetadataFieldBkBizID).
		Group(hamodel.DbmMetadataFieldBkBizID).Find(&bkBizIDs).Error

	if err != nil {
		return bkBizIDs, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return bkBizIDs, nil
}

// ReadMetadataCacheWithBizID reads metadata cache in batches for the given bizID.
func (ha *DbhaData) ReadMetadataCacheWithBizID(bizID int, batchCnt int,
	offsetDuration time.Duration) (metaData []*hamodel.DbmMetadata, err error) {

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	for {
		var batches []*hamodel.DbmMetadata

		err = ha.DB.DB().Model(&hamodel.DbmMetadata{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbmMetadataFieldUpdatedAt),
				map[string]any{"updatedAt": lastUpdateTime}).
			Where(hamodel.DbmMetadataFieldBkBizID, bizID).
			Order(fmt.Sprintf("%s asc", hamodel.DbmMetadataFieldUpdatedAt)).
			Limit(batchCnt).Find(&batches).Error

		if err != nil {
			return nil, gerrors.NewE(gerrors.MysqlFailure, err)
		}

		readCnt := len(batches)
		if readCnt == 0 {
			// no date to read
			break
		}

		// Save the batches into the cache.
		metaData = append(metaData, batches...)

		// update cursor
		lastUpdateTime = batches[readCnt-1].UpdatedAt
	}

	return
}

// ReadDbStatus read db status
func (ha *DbhaData) ReadDbStatus(batchCnt int, offsetDuration time.Duration) (
	dbStatus []*hamodel.DbhaDataStatus, err error) {

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	for {
		var batches []*hamodel.DbhaDataStatus

		err = ha.DB.DB().Model(&hamodel.DbhaDataStatus{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbhaStatusFieldUpdatedAt),
				map[string]any{"updatedAt": lastUpdateTime}).
			Order(fmt.Sprintf("%s asc", hamodel.DbhaStatusFieldUpdatedAt)).
			Limit(batchCnt).Find(&batches).Error

		if err != nil {
			return nil, gerrors.NewE(gerrors.MysqlFailure, err)
		}

		readCnt := len(batches)
		if readCnt == 0 {
			// no date to read
			break
		}

		// Save the batches into the cache.
		dbStatus = append(dbStatus, batches...)

		// update cursor
		lastUpdateTime = batches[readCnt-1].UpdatedAt
	}

	return
}

// ReadDbStatusWithDbInstances read db status with db instances
func (ha *DbhaData) ReadDbStatusWithDbInstances(dbInstances []*DbInstance,
	offsetDuration time.Duration) (dbStatus []*hamodel.DbhaDataStatus, err error) {

	if len(dbInstances) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "no db instances")
	}

	conditions := [][]any{}
	for _, inst := range dbInstances {
		conditions = append(conditions, []any{inst.BkCloudID, inst.IP, inst.Port})
	}

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	err = ha.DB.DB().Model(hamodel.DbhaDataStatus{}).
		Where(fmt.Sprintf("(%s, %s, %s) in ?", hamodel.DbhaStatusFieldBkCloudID,
			hamodel.DbhaStatusFieldDbIp, hamodel.DbhaStatusFieldDbPort), conditions).
		Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbhaStatusFieldUpdatedAt),
			map[string]any{"updatedAt": lastUpdateTime}).
		Order(fmt.Sprintf("%s asc", hamodel.DbhaStatusFieldUpdatedAt)).
		Find(&dbStatus).Error

	return
}

// SaveSwitchingLog save switching log into database
func (ha *DbhaData) SaveSwitchingLog(ctx context.Context, records ...*hamodel.DbSwitchingLog) error {
	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingLog{}).CreateInBatches(records, 100).Error
	if err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return err
}

// ReadSwitchingStrategyWithBkBizId returns switching strategies for the given business ID.
func (ha *DbhaData) ReadSwitchingStrategyWithBkBizId(ctx context.Context, bkBizId int) ([]*hamodel.DbSwitchingStrategy, error) {
	var strategies []*hamodel.DbSwitchingStrategy

	cond := fmt.Sprintf("(%s = ? or %s = 0) and %s = ?",
		hamodel.DbSwitchingStrategyFieldBkBizID,
		hamodel.DbSwitchingStrategyFieldBkBizID,
		hamodel.DbSwitchingStrategyFieldStatus)

	query := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingStrategy{})
	if e := query.Where(cond, bkBizId, hamodel.StatusTypeEnabled).Order(hamodel.DbSwitchingStrategyFieldID).Find(&strategies).Error; e != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, e)
	}

	return strategies, nil
}

// ReadSkipDbInstancesWithBkBizId returns skip db instances for the given business ID.
func (ha *DbhaData) ReadSkipDbInstancesWithBkBizId(bkBizId int) ([]*hamodel.SkipDbInstance, error) {
	var skipDbInstances []*hamodel.SkipDbInstance

	cond := fmt.Sprintf("%s = ? ", hamodel.SkipDbInstanceFieldBkBizID)

	query := ha.DB.DB().Model(&hamodel.SkipDbInstance{})
	if err := query.Where(cond, bkBizId).Find(&skipDbInstances).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return skipDbInstances, nil
}

// ReadBlackWhiteList returns black-white list records for the given business ID and cloud ID.
func (ha *DbhaData) ReadBlackWhiteList(ctx context.Context, bkBizId int, bkCloudId int) ([]*hamodel.DbBlackWhiteList, error) {
	var blackWhiteList []*hamodel.DbBlackWhiteList

	cond := fmt.Sprintf("%s = ? and %s = ? and %s = ? and %s = ?",
		hamodel.DbBlackWhiteListFieldBkBizID,
		hamodel.DbBlackWhiteListFieldBkCloudID,
		hamodel.DbBlackWhiteListFieldStatus,
		hamodel.DbBlackWhiteListFieldSwitchVersion)

	query := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbBlackWhiteList{})
	if e := query.Where(cond, bkBizId, bkCloudId, hamodel.StatusTypeEnabled,
		hamodel.SwitchVersionV2).Find(&blackWhiteList).Error; e != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, e)
	}

	return blackWhiteList, nil
}

// DbTypeUpdatedCount represents the count of rows grouped by db_type.
type DbTypeUpdatedCount struct {
	DbType haprobe.DbType `gorm:"column:db_type"`
	Count  int64          `gorm:"column:cnt"`
}

// CountDbmMetadataUpdatedWithin counts the DbmMetadata rows updated within the given duration.
func (ha *DbhaData) CountDbmMetadataUpdatedWithin(ctx context.Context,
	offsetDuration time.Duration) ([]*DbTypeUpdatedCount, error) {

	lastUpdateTime := time.Now().Local().Add(-offsetDuration)

	type row struct {
		ClusterType haprobe.DbmMetadataClusterType `gorm:"column:cluster_type"`
		Count       int64                          `gorm:"column:cnt"`
	}

	var rows []row
	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbmMetadata{}).
		Select(fmt.Sprintf("%s AS cluster_type, COUNT(*) AS cnt",
			hamodel.DbmMetadataFieldClusterType,
		)).
		Where(fmt.Sprintf("%s > ?", hamodel.DbmMetadataFieldUpdatedAt), lastUpdateTime).
		Group(hamodel.DbmMetadataFieldClusterType).
		Scan(&rows).Error
	if err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	counters := make(map[haprobe.DbType]int64, len(rows))
	for _, r := range rows {
		dbType := hamodel.DbmMetadata{ClusterType: r.ClusterType}.GetDbType()
		counters[dbType] += r.Count
	}

	result := make([]*DbTypeUpdatedCount, 0, len(counters))
	for k, cnt := range counters {
		result = append(result, &DbTypeUpdatedCount{
			DbType: k,
			Count:  cnt,
		})
	}

	return result, nil
}

// CountDbhaDataStatusUpdatedWithin counts the DbhaDataStatus rows updated within the given duration.
func (ha *DbhaData) CountDbhaDataStatusUpdatedWithin(ctx context.Context,
	offsetDuration time.Duration) ([]*DbTypeUpdatedCount, error) {

	lastUpdateTime := time.Now().Local().Add(-offsetDuration)

	var result []*DbTypeUpdatedCount

	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbhaDataStatus{}).
		Select(fmt.Sprintf("%s AS db_type, COUNT(*) AS cnt",
			hamodel.DbhaStatusFieldDbTypeName,
		)).
		Where(fmt.Sprintf("%s > ?", hamodel.DbhaStatusFieldUpdatedAt), lastUpdateTime).
		Group(hamodel.DbhaStatusFieldDbTypeName).
		Scan(&result).Error
	if err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return result, nil
}

// SaveSwitchingSnapshotLog saves switching snapshot log records into the database.
func (ha *DbhaData) SaveSwitchingSnapshotLog(ctx context.Context, records ...*hamodel.DbSwitchingSnapshotLog) error {
	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingSnapshotLog{}).CreateInBatches(records, 100).Error
	if err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}

// UpdateSwitchingSnapshotLog updates an existing switching snapshot log record in the database.
func (ha *DbhaData) UpdateSwitchingSnapshotLog(ctx context.Context, record *hamodel.DbSwitchingSnapshotLog) error {
	err := ha.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingSnapshotLog{}).
		Where(fmt.Sprintf("%s = ?", hamodel.DbSwitchingSnapshotLogFieldID), record.ID).
		Updates(map[string]any{
			hamodel.DbSwitchingSnapshotLogFieldAction:       record.Action,
			hamodel.DbSwitchingSnapshotLogFieldStatus:       record.Status,
			hamodel.DbSwitchingSnapshotLogFieldInstances:    record.Instances,
			hamodel.DbSwitchingSnapshotLogFieldResult:       record.Result,
			hamodel.DbSwitchingSnapshotLogFieldFinishedTime: record.FinishedTime,
		}).Error
	if err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}
