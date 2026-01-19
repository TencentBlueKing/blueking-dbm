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

package handler

import (
	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	"dbm-services/common/dbha-v2/internal/admin/ginx"
	"dbm-services/common/dbha-v2/internal/admin/strategy"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"

	"github.com/gin-gonic/gin"
)

// StrategyHandler strategy handler
type StrategyHandler struct {
	strategyService *strategy.Strategy
}

// NewStrategyHandler new strategy handler
func NewStrategyHandler(strategyService *strategy.Strategy) *StrategyHandler {
	return &StrategyHandler{
		strategyService: strategyService,
	}
}

// Create creates a strategy
//
//	@ID			openapi_strategy_create
//	@Summary	strategy create
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.StrategyCreateRequest	true	"strategy create request"
//	@Success	201
//	@Router		/api/admin/strategies/ [post]
func (h *StrategyHandler) Create(c *gin.Context) {
	var req serializer.StrategyCreateRequest

	if err := c.ShouldBindJSON(&req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	// todo add check

	strategyInfo := &hamodel.DbSwitchingStrategy{
		Name:                   req.Name,
		BkBizID:                req.BkBizID,
		TriggerEventName:       req.TriggerEventName,
		TriggerEventNameReason: req.TriggerEventNameReason,
		TriggerCount:           req.TriggerCount,
		Priority:               req.Priority,
		Scope:                  req.Scope,
		Action:                 req.Action,
		Description:            req.Description,
		Status:                 hamodel.StatusTypeEnabled,
	}

	if err := h.strategyService.CreateStrategy(strategyInfo); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessCreateResponse(c)
}

// Get gets a strategy
//
//	@ID			openapi_strategy_get
//	@Summary	strategy get
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id				path		int		true	"strategy id"
//	@Param		bk_biz_id		query		int		true	"bk_biz_id"
//	@Success	200				{object}	serializer.StrategyOutputInfo
//	@Router		/api/admin/strategies/{id}/ [get]
func (h *StrategyHandler) Get(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	var req serializer.StrategyRequest
	if err := c.ShouldBind(&req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	strategyInfo, err := h.strategyService.GetStrategy(pathParam.ID, req.BkBizID)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	if strategyInfo == nil || strategyInfo.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	output := serializer.StrategyOutputInfo{
		ID:                     strategyInfo.ID,
		Name:                   strategyInfo.Name,
		BkBizID:                strategyInfo.BkBizID,
		TriggerEventName:       strategyInfo.TriggerEventName,
		TriggerEventNameReason: strategyInfo.TriggerEventNameReason,
		TriggerCount:           strategyInfo.TriggerCount,
		Priority:               strategyInfo.Priority,
		Scope:                  strategyInfo.Scope,
		Action:                 strategyInfo.Action,
		Status:                 strategyInfo.Status,
		Description:            strategyInfo.Description,
		CreatedAt:              strategyInfo.CreatedAt,
		UpdatedAt:              strategyInfo.UpdatedAt,
	}

	ginx.SuccessJSONResponse(c, output)
}
