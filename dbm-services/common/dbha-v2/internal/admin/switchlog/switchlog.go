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

// Package switchlog provides database operations for switchlog tables.
package switchlog

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// SwitchLog db connection
type SwitchLog struct {
	DB *hamysql.GormDB
}

// ListSwitchSnapshotLogs list switch snapshot logs
func (s *SwitchLog) ListSwitchSnapshotLogs(
	ctx context.Context,
	bkBizID int,
	switchStartTime time.Time,
	switchFinishedTime time.Time,
	offset int,
	limit int,
) ([]*hamodel.DbSwitchingSnapshotLog, int64, error) {
	var count int64
	var switchLogs []*hamodel.DbSwitchingSnapshotLog

	query := s.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingSnapshotLog{})

	if bkBizID != 0 {
		bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingSnapshotLogFieldBkBizID)
		query = query.Where(bkBizIDCond, bkBizID)
	}

	if !switchStartTime.IsZero() {
		switchStartTimeCond := fmt.Sprintf("%s > ? ", hamodel.DbSwitchingSnapshotLogFieldStartTime)
		query = query.Where(switchStartTimeCond, switchStartTime)
	}

	if !switchFinishedTime.IsZero() {
		switchFinishedTimeCond := fmt.Sprintf("%s < ? ", hamodel.DbSwitchingSnapshotLogFieldFinishedTime)
		query = query.Where(switchFinishedTimeCond, switchFinishedTime)
	}

	// only return switch records, filter out notify records.
	// historical records have a NULL action (before the column was added) and are kept.
	actionField := hamodel.DbSwitchingSnapshotLogFieldAction
	notifyCond := fmt.Sprintf("(%s IS NULL OR %s != ?)", actionField, actionField)
	query = query.Where(notifyCond, hamodel.SnapshotActionTypeNotify.String())

	if err := query.Count(&count).Error; err != nil {
		return nil, 0, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	if limit > 0 {
		query = query.Offset(offset).Limit(limit)
	}

	idCond := fmt.Sprintf("%s DESC ", hamodel.DbSwitchingSnapshotLogFieldID)
	if err := query.Order(idCond).Find(&switchLogs).Error; err != nil {
		return nil, 0, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return switchLogs, count, nil
}

// GetSwitchSnapshotLogByID get switch snapshot log by id
func (s *SwitchLog) GetSwitchSnapshotLogByID(ctx context.Context, id int) (*hamodel.DbSwitchingSnapshotLog, error) {
	var switchSnapshotLog *hamodel.DbSwitchingSnapshotLog

	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingSnapshotLogFieldID)
	if err := s.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingSnapshotLog{}).
		Where(idCond, id).Find(&switchSnapshotLog).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}
	return switchSnapshotLog, nil
}

// ListSwitchLogInfo list switch log info
func (s *SwitchLog) ListSwitchLogInfo(
	ctx context.Context,
	bkBizID int,
	switchID string,
	ip string,
	port int,
) ([]*hamodel.DbSwitchingLog, error) {
	var switchLogInfos []*hamodel.DbSwitchingLog

	query := s.DB.DB().WithContext(ctx).Model(&hamodel.DbSwitchingLog{})

	if bkBizID != 0 {
		bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingLogFieldBkBizID)
		query = query.Where(bkBizIDCond, bkBizID)
	}

	if switchID != "" {
		switchIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingLogFieldSwitchID)
		query = query.Where(switchIDCond, switchID)
	}

	if ip != "" {
		ipCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingLogFieldDbIP)
		query = query.Where(ipCond, ip)
	}

	if port != 0 {
		portCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingLogFieldDbPort)
		query = query.Where(portCond, port)
	}

	idCond := fmt.Sprintf("%s DESC ", hamodel.DbSwitchingLogFieldID)
	if err := query.Order(idCond).Find(&switchLogInfos).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return switchLogInfos, nil
}
