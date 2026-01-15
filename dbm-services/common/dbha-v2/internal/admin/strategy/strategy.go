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

// Package strategy provides database operations for strategy tables.
package strategy

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

// Strategy db connection
type Strategy struct {
	DB *hamysql.GormDB
}

// CreateStrategy create strategy
func (s *Strategy) CreateStrategy(strategy *hamodel.DbSwitchingStrategy) error {
	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Create(&strategy).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}

// GetStrategy get strategy
func (s *Strategy) GetStrategy(strategyID int, bkBizId int) (*hamodel.DbSwitchingStrategy, error) {
	var strategy *hamodel.DbSwitchingStrategy

	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(idCond, strategyID).Where(bkBizIDCond, bkBizId).Find(&strategy).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return strategy, nil
}

// UpdateStrategy update strategy
func (s *Strategy) UpdateStrategy(strategy hamodel.DbSwitchingStrategy) error {
	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(idCond, strategy.ID).Where(bkBizIDCond, strategy.BkBizID).Select(
		hamodel.DbSwitchingStrategyFieldTriggerEventName,
		hamodel.DbSwitchingStrategyFieldTriggerEventNameReason,
		hamodel.DbSwitchingStrategyFieldPriority,
		hamodel.DbSwitchingStrategyFieldScope,
		hamodel.DbSwitchingStrategyFieldAction,
		hamodel.DbSwitchingStrategyFieldDescription,
	).Updates(&strategy).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}

// UpdateStrategyStatus update strategy status
func (s *Strategy) UpdateStrategyStatus(strategyID int, bkBizId int, status hamodel.StatusType) error {
	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(idCond, strategyID).Where(bkBizIDCond, bkBizId).Updates(map[string]any{
		hamodel.DbSwitchingStrategyFieldStatus: status,
	}).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}
