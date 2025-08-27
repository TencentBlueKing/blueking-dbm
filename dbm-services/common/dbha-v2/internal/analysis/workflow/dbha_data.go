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
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

type dbInstance struct {
	ip   string
	port int
}

type DbhaData struct {
	db *hamysql.DB
}

func (ha *DbhaData) getBizIDs() ([]int, error) {
	bkBizIDs := []int{}

	err := ha.db.DB().Model(&hamodel.DbmMetadata{}).
		Select(hamodel.DbmMetadataFieldBkBizID).
		Group(hamodel.DbmMetadataFieldBkBizID).Find(&bkBizIDs).Error

	if err != nil {
		return bkBizIDs, gerrors.NewE(gerrors.ComponentFailure, err)
	}

	return bkBizIDs, nil
}

func (ha *DbhaData) readMetadataCacheWithBizID(bizID int, batchCnt int) (metaData []*hamodel.DbmMetadata, err error) {
	lastUpdateTime := time.Now().Local().Add(-24 * time.Hour)

	for {
		var batches []*hamodel.DbmMetadata

		err := ha.db.DB().Model(&hamodel.DbmMetadata{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbmMetadataFieldUpdatedAt),
				map[string]interface{}{"updatedAt": lastUpdateTime}).
			Where(hamodel.DbmMetadataFieldBkBizID, bizID).
			Order(fmt.Sprintf("%s asc", hamodel.DbmMetadataFieldUpdatedAt)).
			Limit(batchCnt).Find(&batches).Error

		if err != nil {
			return nil, gerrors.NewE(gerrors.ComponentFailure, err)
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

func (ha *DbhaData) readDbMetricsWithDbInstances(dbInstances []*dbInstance,
	offsetDuration time.Duration) (dbMetrics []*hamodel.DatabaseMetric, err error) {

	if len(dbInstances) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "no db instances")
	}

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	query := ha.db.DB().Model(&hamodel.DatabaseMetric{})
	hasCondition := false

	for _, inst := range dbInstances {
		if hasCondition {
			query = query.Or(fmt.Sprintf("%s like ? and %s = ?", hamodel.DatabaseMetricFieldIPs,
				hamodel.DatabaseMetricFieldInstanceID), inst.ip, inst.port)
			continue
		}

		query = query.Where(fmt.Sprintf("%s like ? and %s = ?", hamodel.DatabaseMetricFieldIPs,
			hamodel.DatabaseMetricFieldInstanceID), inst.ip, inst.port)
		hasCondition = true
	}

	queryErr := query.Where(fmt.Sprintf("%s > @updatedAt", hamodel.DatabaseMetricFieldUpdatedAt),
		map[string]any{"updatedAt": lastUpdateTime}).
		Order(fmt.Sprintf("%s asc", hamodel.DatabaseMetricFieldUpdatedAt)).
		Find(&dbMetrics).Error

	if queryErr != nil {
		err = gerrors.NewE(gerrors.ComponentFailure, queryErr)
		return
	}

	return
}

func (ha *DbhaData) readDbEventWithDbInstances(dbInstances []*dbInstance,
	offsetDuration time.Duration) (events []*hamodel.DbEvent, err error) {

	if len(dbInstances) == 0 {
		return nil, gerrors.New(gerrors.InvalidParameter, "no db instances")
	}

	conditions := [][]interface{}{}
	for _, instance := range dbInstances {
		conditions = append(conditions, []interface{}{instance.ip, instance.port})
	}

	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	err = ha.db.DB().Model(&hamodel.DbEvent{}).
		Where(fmt.Sprintf("(%s, %s) in ?", hamodel.DbEventFieldIP, hamodel.DbEventFieldPort), conditions).
		Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbEventFieldUpdatedAt),
			map[string]interface{}{"updatedAt": lastUpdateTime}).
		Order(fmt.Sprintf("%s asc", hamodel.DbEventFieldUpdatedAt)).Find(&events).Error

	if err != nil {
		return nil, gerrors.NewE(gerrors.ComponentFailure, err)
	}

	return
}

func (ha *DbhaData) readAllDbEvent(batchCnt int, offsetDuration time.Duration) (events []*hamodel.DbEvent, err error) {
	lastUpdateTime := time.Now().Local().Add(offsetDuration)

	for {
		var batches []*hamodel.DbEvent

		err := ha.db.DB().Model(&hamodel.DbEvent{}).
			Where(fmt.Sprintf("%s > @updatedAt", hamodel.DbEventFieldUpdatedAt),
				map[string]interface{}{"updatedAt": lastUpdateTime}).
			Order(fmt.Sprintf("%s asc", hamodel.DbEventFieldUpdatedAt)).
			Limit(batchCnt).Find(&batches).Error

		if err != nil {
			return nil, gerrors.NewE(gerrors.ComponentFailure, err)
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
