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

package serializer

import (
	"time"

	"dbm-services/common/dbha-v2/internal/admin/strategy"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	validator "github.com/go-playground/validator/v10"
)

// StrategyPathParam strategy path param
type StrategyPathParam struct {
	ID int `json:"id" uri:"id" binding:"required"`
}

// StrategyRequest strategy request
type StrategyRequest struct {
	BkBizID int    `json:"bk_biz_id"      form:"bk_biz_id" binding:"required"`
	Name    string `json:"name,omitempty" form:"name"`
}

// StrategyInfo strategy info
type StrategyInfo struct {
	ID               int                     `json:"id"`
	Name             string                  `json:"name"               binding:"required"`
	BkBizID          int                     `json:"bk_biz_id"          binding:"required"`
	TriggerEventName haprobe.DbEventName     `json:"trigger_event_name" validate:"triggerEventName"`
	TriggerCount     int                     `json:"trigger_count"      validate:"triggerCount"`
	Priority         int                     `json:"priority"           validate:"priority"`
	Scope            hamodel.ActionScopeType `json:"scope"              validate:"scope"`
	Action           hamodel.ActionType      `json:"action"             validate:"action"`
	Description      string                  `json:"description"`
}

// StrategyCreateRequest strategy create request
type StrategyCreateRequest struct {
	StrategyInfo
}

// StrategyUpdateRequest strategy update request
type StrategyUpdateRequest struct {
	StrategyInfo
}

// StrategyListRequest strategy list request
type StrategyListRequest struct {
	StrategyRequest
	Scope  string `json:"scope"  form:"scope"`
	Action string `json:"action" form:"action"`
	Status string `json:"status" form:"status"`
	Offset int    `json:"offset" form:"offset"`
	Limit  int    `json:"limit"  form:"limit"`
}

// StrategyStatusUpdateRequest strategy status update request
type StrategyStatusUpdateRequest struct {
	BkBizID int                `json:"bk_biz_id" binding:"required"`
	Status  hamodel.StatusType `json:"status"    binding:"required" validate:"status"`
}

// StrategyListResponse strategy list response
type StrategyListResponse []StrategyOutputInfo

// StrategyOutputInfo strategy output info
type StrategyOutputInfo struct {
	StrategyInfo
	Status    hamodel.StatusType `json:"status"`
	CreatedAt time.Time          `json:"created_at"`
	UpdatedAt time.Time          `json:"updated_at"`
}

// StrategyBatchCreateRequest strategy batch create request
type StrategyBatchCreateRequest struct {
	BkBizID int            `json:"bk_biz_id" binding:"required"`
	Data    []StrategyInfo `json:"data"      binding:"required"`
}

// StrategyBatchUpdateRequest strategy batch update request
type StrategyBatchUpdateRequest struct {
	BkBizID int            `json:"bk_biz_id" binding:"required"`
	Data    []StrategyInfo `json:"data"      binding:"required"`
}

// StrategyBatchDeleteRequest strategy batch delete request
type StrategyBatchDeleteRequest struct {
	BkBizID int   `json:"bk_biz_id" binding:"required"`
	IDs     []int `json:"ids"       binding:"required"`
}

// StrategyBatchUpdateStatusRequest strategy batch update status request
type StrategyBatchUpdateStatusRequest struct {
	IDs     []int              `json:"ids"       binding:"required"`
	BkBizID int                `json:"bk_biz_id" binding:"required"`
	Status  hamodel.StatusType `json:"status"    binding:"required" validate:"status"`
}

// GlobalStrategyCreateRequest global strategy create request
type GlobalStrategyCreateRequest struct {
	Name             string                  `json:"name"               binding:"required"`
	TriggerEventName haprobe.DbEventName     `json:"trigger_event_name" validate:"triggerEventName"`
	TriggerCount     int                     `json:"trigger_count"      validate:"triggerCount"`
	Priority         int                     `json:"priority"           validate:"priority"`
	Scope            hamodel.ActionScopeType `json:"scope"              validate:"scope"`
	Action           hamodel.ActionType      `json:"action"             validate:"action"`
	Description      string                  `json:"description"`
}

// GlobalStrategyListRequest global strategy list request
type GlobalStrategyListRequest struct {
	Name   string `json:"name"   form:"name"`
	Scope  string `json:"scope"  form:"scope"`
	Action string `json:"action" form:"action"`
	Status string `json:"status" form:"status"`
	Offset int    `json:"offset" form:"offset"`
	Limit  int    `json:"limit"  form:"limit"`
}

// GlobalStrategyUpdateRequest global strategy update request
type GlobalStrategyUpdateRequest struct {
	Name             string                  `json:"name"               binding:"required"`
	TriggerEventName haprobe.DbEventName     `json:"trigger_event_name" validate:"triggerEventName"`
	TriggerCount     int                     `json:"trigger_count"      validate:"triggerCount"`
	Priority         int                     `json:"priority"           validate:"priority"`
	Scope            hamodel.ActionScopeType `json:"scope"              validate:"scope"`
	Action           hamodel.ActionType      `json:"action"             validate:"action"`
	Description      string                  `json:"description"`
}

// GlobalStrategyStatusUpdateRequest global strategy status update request
type GlobalStrategyStatusUpdateRequest struct {
	Status hamodel.StatusType `json:"status"    binding:"required" validate:"status"`
}

// CheckDuplicatedName check duplicated name
func CheckDuplicatedName(s *strategy.Strategy, id int, bkBizID int, name string) (bool, error) {
	return s.DuplicatedName(id, bkBizID, name)
}

// BatchCreateCheckDuplicatedName batch create check duplicated name
func BatchCreateCheckDuplicatedName(s *strategy.Strategy, bkBizID int, names []string) (bool, error) {
	queryMap := map[string]any{
		"bk_biz_id": bkBizID,
		"name":      names,
	}
	strategies, err := s.QueryStrategies(queryMap)
	if err != nil {
		return false, err
	}

	if len(strategies) > 0 {
		return true, nil
	}

	return false, nil
}

// BatchUpdateCheckDuplicatedName batch update check duplicated name
func BatchUpdateCheckDuplicatedName(s *strategy.Strategy, bkBizID int, names []string, nameIDMap map[string]int) (bool, error) {
	queryMap := map[string]any{
		"bk_biz_id": bkBizID,
		"name":      names,
	}
	strategies, err := s.QueryStrategies(queryMap)
	if err != nil {
		return false, err
	}

	currentStrategyNameIDMap := make(map[string]int)
	for _, strategyInfo := range strategies {
		currentStrategyNameIDMap[strategyInfo.Name] = strategyInfo.ID
	}

	for name, id := range nameIDMap {
		if _, ok := currentStrategyNameIDMap[name]; !ok {
			continue
		}
		if currentStrategyNameIDMap[name] != id {
			return true, nil
		}
	}

	return false, nil
}

// CheckTriggerEventName check trigger_event_name
func CheckTriggerEventName(fl validator.FieldLevel) bool {
	value := fl.Field().String()
	if _, ok := haprobe.DbEventNameMap[haprobe.DbEventName(value)]; !ok {
		return false
	}
	return true
}

// CheckTriggerCount check trigger_count
func CheckTriggerCount(fl validator.FieldLevel) bool {
	value := fl.Field().Int()
	if value <= 0 {
		return false
	}
	return true
}

// CheckPriority check priority
func CheckPriority(fl validator.FieldLevel) bool {
	value := fl.Field().Int()
	if value < 0 {
		return false
	}
	return true
}

// CheckScope check scope
func CheckScope(fl validator.FieldLevel) bool {
	value := fl.Field().String()
	if _, ok := hamodel.ActionScopeTypeMap[hamodel.ActionScopeType(value)]; !ok {
		return false
	}
	return true
}

// CheckAction check action
func CheckAction(fl validator.FieldLevel) bool {
	value := fl.Field().String()
	if _, ok := hamodel.ActionTypeMap[hamodel.ActionType(value)]; !ok {
		return false
	}
	return true
}

// CheckStatus check status
func CheckStatus(fl validator.FieldLevel) bool {
	value := fl.Field().String()
	if _, ok := hamodel.StatusTypeMap[hamodel.StatusType(value)]; !ok {
		return false
	}
	return true
}

func init() {
	hanet.AddValidation("triggerEventName", CheckTriggerEventName, "event name is invalid")
	hanet.AddValidation("triggerCount", CheckTriggerCount, "must be greater than 0")
	hanet.AddValidation("priority", CheckPriority, "must be greater than or equal to 0")
	hanet.AddValidation("scope", CheckScope, "must be one of cluster, host")
	hanet.AddValidation("action", CheckAction, "must be one of notify, switch")
	hanet.AddValidation("status", CheckStatus, "must be one of enabled, disabled")
}
