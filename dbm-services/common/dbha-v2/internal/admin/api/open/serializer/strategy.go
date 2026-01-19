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

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// StrategyPathParam strategy path param
type StrategyPathParam struct {
	ID int `json:"id" uri:"id" binding:"required"`
}

// StrategyRequest strategy request
type StrategyRequest struct {
	BkBizID int    `json:"bk_biz_id" form:"bk_biz_id" binding:"required"`
	Name    string `json:"name,omitempty" form:"name"`
}

// StrategyCreateRequest strategy create request
type StrategyCreateRequest struct {
	Name                   string                    `json:"name" binding:"required"`
	BkBizID                int                       `json:"bk_biz_id" binding:"required"`
	TriggerEventName       haprobe.DbEventName       `json:"trigger_event_name" binding:"required"`
	TriggerEventNameReason haprobe.DbEventNameReason `json:"trigger_event_name_reason" binding:"required,min=0"`
	TriggerCount           int                       `json:"trigger_count" binding:"required,min=1"`
	Priority               int                       `json:"priority" binding:"required,min=0"`
	Scope                  hamodel.ActionScopeType   `json:"scope" binding:"required"`
	Action                 hamodel.ActionType        `json:"action" binding:"required"`
	Description            string                    `json:"description"`
}

// StrategyOutputInfo strategy output info
type StrategyOutputInfo struct {
	ID                     int                       `json:"id"`
	Name                   string                    `json:"name"`
	BkBizID                int                       `json:"bk_biz_id"`
	TriggerEventName       haprobe.DbEventName       `json:"trigger_event_name"`
	TriggerEventNameReason haprobe.DbEventNameReason `json:"trigger_event_name_reason"`
	TriggerCount           int                       `json:"trigger_count"`
	Priority               int                       `json:"priority"`
	Scope                  hamodel.ActionScopeType   `json:"scope"`
	Action                 hamodel.ActionType        `json:"action"`
	Status                 hamodel.StatusType        `json:"status"`
	Description            string                    `json:"description"`
	CreatedAt              time.Time                 `json:"created_at"`
	UpdatedAt              time.Time                 `json:"updated_at"`
}
