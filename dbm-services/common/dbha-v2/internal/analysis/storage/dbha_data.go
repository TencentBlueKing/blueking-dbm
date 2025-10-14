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
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

type DbInstance struct {
	BkCloudID int
	IP        string
	Port      int
}

type DbhaData struct {
	DB *hamysql.DB
}

func (ha *DbhaData) GetBizIDs() ([]int, error) {
	bkBizIDs := []int{}

	err := ha.DB.DB().Model(&hamodel.DbmMetadata{}).
		Select(hamodel.DbmMetadataFieldBkBizID).
		Group(hamodel.DbmMetadataFieldBkBizID).Find(&bkBizIDs).Error

	if err != nil {
		return bkBizIDs, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return bkBizIDs, nil
}

func (ha *DbhaData) ReadMetadataCacheWithBizID(bizID int, batchCnt int) (metaData []*hamodel.DbmMetadata, err error) {
	lastUpdateTime := time.Now().Local().Add(-24 * time.Hour)

	for {
		var batches []*hamodel.DbmMetadata

		err := ha.DB.DB().Model(&hamodel.DbmMetadata{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbmMetadataFieldUpdatedAt),
				map[string]interface{}{"updatedAt": lastUpdateTime}).
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

func (ha *DbhaData) ReadDbMetricsWithDbInstances(dbInstances []*DbInstance,
	offsetDuration time.Duration) (dbMetrics []*hamodel.DatabaseMetric, err error) {

	if len(dbInstances) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "no db instances")
	}

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	query := ha.DB.DB().Model(&hamodel.DatabaseMetric{})
	hasCondition := false

	for _, inst := range dbInstances {
		if hasCondition {
			query = query.Or(fmt.Sprintf("%s like ? and %s = ?", hamodel.DatabaseMetricFieldIPs,
				hamodel.DatabaseMetricFieldInstanceID), inst.IP, inst.Port)
			continue
		}

		query = query.Where(fmt.Sprintf("%s like ? and %s = ?", hamodel.DatabaseMetricFieldIPs,
			hamodel.DatabaseMetricFieldInstanceID), inst.IP, inst.Port)
		hasCondition = true
	}

	queryErr := query.Where(fmt.Sprintf("%s > @updatedAt", hamodel.DatabaseMetricFieldUpdatedAt),
		map[string]any{"updatedAt": lastUpdateTime}).
		Order(fmt.Sprintf("%s asc", hamodel.DatabaseMetricFieldUpdatedAt)).
		Find(&dbMetrics).Error

	if queryErr != nil {
		err = gerrors.NewE(gerrors.MysqlFailure, queryErr)
		return
	}

	return
}

func (ha *DbhaData) ReadDbEventWithDbInstances(dbInstances []*DbInstance,
	offsetDuration time.Duration) (events []*hamodel.DbEvent, err error) {

	if len(dbInstances) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "no db instances")
	}

	conditions := [][]any{}
	for _, instance := range dbInstances {
		conditions = append(conditions, []any{instance.BkCloudID, instance.IP, instance.Port})
	}

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	err = ha.DB.DB().Model(&hamodel.DbEvent{}).
		Where(fmt.Sprintf("(%s, %s, %s) in ?", hamodel.DbEventFieldBkCloudID,
			hamodel.DbEventFieldIP, hamodel.DbEventFieldPort), conditions).
		Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbEventFieldUpdatedAt),
			map[string]any{"updatedAt": lastUpdateTime}).
		Order(fmt.Sprintf("%s asc", hamodel.DbEventFieldUpdatedAt)).Find(&events).Error

	if err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return
}

func (ha *DbhaData) ReadAllDbEvent(batchCnt int, offsetDuration time.Duration) (events []*hamodel.DbEvent, err error) {
	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	for {
		var batches []*hamodel.DbEvent

		err := ha.DB.DB().Model(&hamodel.DbEvent{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbEventFieldUpdatedAt),
				map[string]any{"updatedAt": lastUpdateTime}).
			Order(fmt.Sprintf("%s asc", hamodel.DbEventFieldUpdatedAt)).
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
		events = append(events, batches...)

		// update cursor
		lastUpdateTime = batches[readCnt-1].UpdatedAt
	}

	return
}

func (ha *DbhaData) ReadAllDbEventWithoutMetadata(batchCnt int, offsetDuration time.Duration) (
	events []*hamodel.DbEvent, err error) {

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	for {
		var batches []*hamodel.DbEvent

		err = ha.DB.DB().Model(&hamodel.DbEvent{}).
			Select(fmt.Sprintf("%s.*", hamodel.DbEventTableName)).
			Joins(fmt.Sprintf("left join %s on %s.%s = %s.%s and %s.%s = %s.%s and %s.%s = %s.%s",
				hamodel.DbmMetadataTableName,

				hamodel.DbEventTableName,
				hamodel.DbEventFieldBkCloudID,

				hamodel.DbmMetadataTableName,
				hamodel.DbmMetadataFieldBkCloudID,

				hamodel.DbEventTableName,
				hamodel.DbEventFieldIP,

				hamodel.DbmMetadataTableName,
				hamodel.DbmMetadataFieldListenIP,

				hamodel.DbEventTableName,
				hamodel.DbEventFieldPort,

				hamodel.DbmMetadataTableName,
				hamodel.DbmMetadataFieldListenPort,
			)).
			Where(fmt.Sprintf("%s.%s is null",
				hamodel.DbmMetadataTableName,
				hamodel.DbmMetadataFieldCreatedAt,
			)).
			Where(fmt.Sprintf("%s.%s > @updatedAt",
				hamodel.DbEventTableName,
				hamodel.DbEventFieldUpdatedAt),
				map[string]any{"updatedAt": lastUpdateTime}).
			Order(fmt.Sprintf("%s asc", hamodel.DbEventFieldUpdatedAt)).
			Find(&batches).Error

		if err != nil {
			return nil, gerrors.NewE(gerrors.MysqlFailure, err)
		}

		readCnt := len(batches)
		if readCnt == 0 {
			// no date to read
			break
		}

		// Save the batches into the cache.
		events = append(events, batches...)

		// update cursor
		lastUpdateTime = batches[readCnt-1].UpdatedAt
	}

	return
}

func (ha *DbhaData) SaveSwitchingLog(records ...*hamodel.DbSwitchingLog) error {
	err := ha.DB.DB().Model(&hamodel.DbSwitchingLog{}).CreateInBatches(records, 100).Error
	if err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return err
}

func (ha *DbhaData) ReadSwitchingStrategyWithBkBizID(bkBizID int) ([]*hamodel.DbSwitchingStrategy, error) {
	var strategies []*hamodel.DbSwitchingStrategy

	cond := fmt.Sprintf("%s = ? or %s = 0 ", hamodel.DbSwitchingStrategyFieldBkBizID,
		hamodel.DbSwitchingStrategyFieldBkBizID)

	query := ha.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if e := query.Where(cond, bkBizID).Find(&strategies).Error; e != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, e)
	}

	return strategies, nil
}

func (ha *DbhaData) ReadSkipDbInstancesWithBkBizID(bkBizID int) ([]*hamodel.SkipDbInstance, error) {
	var skipDbInstances []*hamodel.SkipDbInstance

	cond := fmt.Sprintf("%s = ? ", hamodel.SkipDbInstanceFieldBkBizID)

	query := ha.DB.DB().Model(&hamodel.SkipDbInstance{})
	if err := query.Where(cond, bkBizID).Find(&skipDbInstances).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return skipDbInstances, nil
}
