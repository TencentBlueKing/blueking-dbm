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
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
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
func (s *Strategy) GetStrategy(strategyID int, bkBizID int) (*hamodel.DbSwitchingStrategy, error) {
	var strategy *hamodel.DbSwitchingStrategy

	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
	statusCond := fmt.Sprintf("%s in ? ", hamodel.DbSwitchingStrategyFieldStatus)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(idCond, strategyID).Where(bkBizIDCond, bkBizID).
		Where(statusCond, []hamodel.StatusType{hamodel.StatusTypeEnabled, hamodel.StatusTypeDisabled}).
		Find(&strategy).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return strategy, nil
}

// ListStrategies list strategies
func (s *Strategy) ListStrategies(
	bkBizID int,
	name string,
	scope string,
	action string,
	status string,
	offset int,
	limit int,
) ([]*hamodel.DbSwitchingStrategy, int64, error) {
	var count int64
	var strategies []*hamodel.DbSwitchingStrategy

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})

	if name != "" {
		nameCond := fmt.Sprintf("%s LIKE ? ", hamodel.DbSwitchingStrategyFieldName)
		query = query.Where(nameCond, "%"+name+"%")
	}

	if scope != "" {
		scopeCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldScope)
		query = query.Where(scopeCond, scope)
	}

	if action != "" {
		actionCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldAction)
		query = query.Where(actionCond, action)
	}

	if status != "" {
		statusCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldStatus)
		if _, ok := hamodel.StatusTypeMap[hamodel.StatusType(status)]; !ok {
			status = hamodel.StatusTypeEnabled.String()
		}
		query = query.Where(statusCond, status)
	} else {
		statusCond := fmt.Sprintf("%s in ? ", hamodel.DbSwitchingStrategyFieldStatus)
		query = query.Where(statusCond, []hamodel.StatusType{hamodel.StatusTypeEnabled, hamodel.StatusTypeDisabled})
	}

	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
	if err := query.Where(bkBizIDCond, bkBizID).Count(&count).Error; err != nil {
		return nil, 0, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	createdAtCond := fmt.Sprintf("%s DESC ", hamodel.DbSwitchingStrategyFieldCreatedAt)
	if err := query.Offset(offset).Limit(limit).Order(createdAtCond).Find(&strategies).Error; err != nil {
		return nil, 0, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return strategies, count, nil
}

// DuplicatedName check if name is duplicated
func (s *Strategy) DuplicatedName(strategyID int, bkBizID int, name string) (bool, error) {
	var strategies []*hamodel.DbSwitchingStrategy

	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	nameCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldName)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{}).Where(bkBizIDCond, bkBizID).Where(nameCond, name)
	if strategyID != 0 {
		query = query.Not(idCond, strategyID)
	}

	if err := query.Find(&strategies).Error; err != nil {
		return true, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	if len(strategies) == 0 {
		return false, nil
	}

	return true, nil
}

// QueryStrategies query strategies
func (s *Strategy) QueryStrategies(params map[string]any) ([]*hamodel.DbSwitchingStrategy, error) {
	var strategies []*hamodel.DbSwitchingStrategy

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(params).Find(&strategies).Error; err != nil {
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return strategies, nil
}

// UpdateStrategy update strategy
func (s *Strategy) UpdateStrategy(strategy *hamodel.DbSwitchingStrategy) error {
	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
	statusCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldStatus)

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Where(idCond, strategy.ID).Where(bkBizIDCond, strategy.BkBizID).
		Not(statusCond, hamodel.StatusTypeDeleted).Select(
		hamodel.DbSwitchingStrategyFieldName,
		hamodel.DbSwitchingStrategyFieldTriggerEventName,
		hamodel.DbSwitchingStrategyFieldTriggerCount,
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
func (s *Strategy) UpdateStrategyStatus(strategyID int, bkBizID int, status hamodel.StatusType) error {
	idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
	params := map[string]any{
		hamodel.DbSwitchingStrategyFieldStatus: status,
	}

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{}).Where(idCond, strategyID).Where(bkBizIDCond, bkBizID)

	if status == hamodel.StatusTypeDeleted {
		params[hamodel.DbSwitchingStrategyFieldDeletedAt] = time.Now()
	} else {
		statusCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldStatus)
		query = query.Not(statusCond, hamodel.StatusTypeDeleted)
	}

	if err := query.Updates(params).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}

// BatchCreateStrategy batch create strategy
func (s *Strategy) BatchCreateStrategy(strategies []*hamodel.DbSwitchingStrategy) error {
	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{})
	if err := query.Create(&strategies).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}

// BatchUpdateStrategy batch update strategy
func (s *Strategy) BatchUpdateStrategy(strategies []*hamodel.DbSwitchingStrategy) error {
	return s.DB.DB().Transaction(func(tx *gorm.DB) error {
		for _, strategyItem := range strategies {
			idCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldID)
			bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
			statusCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldStatus)

			if err := tx.Model(&hamodel.DbSwitchingStrategy{}).
				Where(idCond, strategyItem.ID).
				Where(bkBizIDCond, strategyItem.BkBizID).
				Not(statusCond, hamodel.StatusTypeDeleted).
				Select(
					hamodel.DbSwitchingStrategyFieldName,
					hamodel.DbSwitchingStrategyFieldTriggerEventName,
					hamodel.DbSwitchingStrategyFieldTriggerCount,
					hamodel.DbSwitchingStrategyFieldPriority,
					hamodel.DbSwitchingStrategyFieldScope,
					hamodel.DbSwitchingStrategyFieldAction,
					hamodel.DbSwitchingStrategyFieldDescription,
				).Updates(strategyItem).Error; err != nil {
				return gerrors.NewE(gerrors.MysqlFailure, err)
			}
		}
		return nil
	})
}

// BatchUpdateStrategyStatus batch update strategy status
func (s *Strategy) BatchUpdateStrategyStatus(strategyIDs []int, bkBizID int, status hamodel.StatusType) error {
	idsCond := fmt.Sprintf("%s IN ? ", hamodel.DbSwitchingStrategyFieldID)
	bkBizIDCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldBkBizID)
	params := map[string]any{
		hamodel.DbSwitchingStrategyFieldStatus: status,
	}

	query := s.DB.DB().Model(&hamodel.DbSwitchingStrategy{}).Where(idsCond, strategyIDs).Where(bkBizIDCond, bkBizID)

	if status == hamodel.StatusTypeDeleted {
		params[hamodel.DbSwitchingStrategyFieldDeletedAt] = time.Now()
	} else {
		statusCond := fmt.Sprintf("%s = ? ", hamodel.DbSwitchingStrategyFieldStatus)
		query = query.Not(statusCond, hamodel.StatusTypeDeleted)
	}

	if err := query.Updates(params).Error; err != nil {
		return gerrors.NewE(gerrors.MysqlFailure, err)
	}

	return nil
}
