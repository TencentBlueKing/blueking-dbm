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
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

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
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	isDuplicated, err := serializer.CheckDuplicatedName(h.strategyService, 0, req.BkBizID, req.Name)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	strategyInfo := &hamodel.DbSwitchingStrategy{
		Name:             req.Name,
		BkBizID:          req.BkBizID,
		TriggerEventName: req.TriggerEventName,
		TriggerCount:     req.TriggerCount,
		Priority:         req.Priority,
		Scope:            req.Scope,
		Action:           req.Action,
		Description:      req.Description,
		Status:           hamodel.StatusTypeEnabled,
	}

	if err := h.strategyService.CreateStrategy(strategyInfo); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessCreateResponse(c)
}

// BatchCreate batch creates strategies
//
//	@ID			openapi_strategy_batch_create
//	@Summary	strategy batch create
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.StrategyBatchCreateRequest	true	"strategy batch create request"
//	@Success	201
//	@Router		/api/admin/strategies/batch/ [post]
func (h *StrategyHandler) BatchCreate(c *gin.Context) {
	var req serializer.StrategyBatchCreateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	names := make([]string, 0, len(req.Data))
	nameIDMap := map[string]int{}
	strategies := make([]*hamodel.DbSwitchingStrategy, 0, len(req.Data))
	for _, strategyInfo := range req.Data {
		if _, ok := nameIDMap[strategyInfo.Name]; ok {
			ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
			return
		}

		names = append(names, strategyInfo.Name)
		nameIDMap[strategyInfo.Name] = strategyInfo.ID
		strategies = append(strategies, &hamodel.DbSwitchingStrategy{
			Name:             strategyInfo.Name,
			BkBizID:          strategyInfo.BkBizID,
			TriggerEventName: strategyInfo.TriggerEventName,
			TriggerCount:     strategyInfo.TriggerCount,
			Priority:         strategyInfo.Priority,
			Scope:            strategyInfo.Scope,
			Action:           strategyInfo.Action,
			Description:      strategyInfo.Description,
			Status:           hamodel.StatusTypeEnabled,
		})
	}

	isDuplicated, err := serializer.BatchCreateCheckDuplicatedName(h.strategyService, req.BkBizID, names)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	if err := h.strategyService.BatchCreateStrategy(strategies); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessCreateResponse(c)
}

// BatchUpdate batch updates strategies
//
//	@ID			openapi_strategy_batch_update
//	@Summary	strategy batch update
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.StrategyBatchUpdateRequest	true	"strategy batch update request"
//	@Success	204
//	@Router		/api/admin/strategies/batch/ [put]
func (h *StrategyHandler) BatchUpdate(c *gin.Context) {
	var req serializer.StrategyBatchUpdateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	names := make([]string, 0, len(req.Data))
	nameIDMap := map[string]int{}
	strategies := make([]*hamodel.DbSwitchingStrategy, 0, len(req.Data))
	for _, strategyInfo := range req.Data {
		if _, ok := nameIDMap[strategyInfo.Name]; ok {
			ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
			return
		}

		names = append(names, strategyInfo.Name)
		nameIDMap[strategyInfo.Name] = strategyInfo.ID
		strategies = append(strategies, &hamodel.DbSwitchingStrategy{
			ID:               strategyInfo.ID,
			Name:             strategyInfo.Name,
			BkBizID:          strategyInfo.BkBizID,
			TriggerEventName: strategyInfo.TriggerEventName,
			TriggerCount:     strategyInfo.TriggerCount,
			Priority:         strategyInfo.Priority,
			Scope:            strategyInfo.Scope,
			Action:           strategyInfo.Action,
			Description:      strategyInfo.Description,
		})
	}

	isDuplicated, err := serializer.BatchUpdateCheckDuplicatedName(h.strategyService, req.BkBizID, names, nameIDMap)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	if err := h.strategyService.BatchUpdateStrategy(strategies); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// BatchDelete batch deletes strategies
//
//	@ID			openapi_strategy_batch_delete
//	@Summary	strategy batch delete
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.StrategyBatchDeleteRequest	true	"strategy batch delete request"
//	@Success	204
//	@Router		/api/admin/strategies/batch/ [delete]
func (h *StrategyHandler) BatchDelete(c *gin.Context) {
	var req serializer.StrategyBatchDeleteRequest
	if err := c.ShouldBind(&req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	if err := h.strategyService.BatchUpdateStrategyStatus(req.IDs, req.BkBizID, hamodel.StatusTypeDeleted); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// BatchUpdateStatus batch updates strategies status
//
//	@ID			openapi_strategy_batch_update_status
//	@Summary	strategy batch update status
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.StrategyBatchUpdateStatusRequest	true	"strategy batch update status request"
//	@Success	204
//	@Router		/api/admin/strategies/batch/status/ [put]
func (h *StrategyHandler) BatchUpdateStatus(c *gin.Context) {
	var req serializer.StrategyBatchUpdateStatusRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	if err := h.strategyService.BatchUpdateStrategyStatus(req.IDs, req.BkBizID, req.Status); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// TriggerEventNamesList lists trigger event names
//
//	@ID			openapi_strategy_trigger_event_names_list
//	@Summary	strategy trigger event names list
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Success	200	{object}	[]string
//	@Router		/api/admin/strategies/eventnames/ [get]
func (h *StrategyHandler) TriggerEventNamesList(c *gin.Context) {
	ginx.SuccessJSONResponse(c, haprobe.DbEventNameList)
}

// List lists strategies
//
//	@ID			openapi_strategy_list
//	@Summary	strategy list
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	query		serializer.StrategyListRequest	false	"query parameters"
//	@Success	200		{object}	ginx.PaginatedResponse{results=serializer.StrategyListResponse}
//	@Router		/api/admin/strategies/ [get]
func (h *StrategyHandler) List(c *gin.Context) {
	var req serializer.StrategyListRequest
	if err := c.ShouldBind(&req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	strategies, count, err := h.strategyService.ListStrategies(
		req.BkBizID,
		req.Name,
		req.Scope,
		req.Action,
		req.Status,
		ginx.GetOffset(c),
		ginx.GetLimit(c),
	)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	var output serializer.StrategyListResponse

	for _, strategyInfo := range strategies {
		output = append(output, serializer.StrategyOutputInfo{
			StrategyInfo: serializer.StrategyInfo{
				ID:               strategyInfo.ID,
				Name:             strategyInfo.Name,
				BkBizID:          strategyInfo.BkBizID,
				TriggerEventName: strategyInfo.TriggerEventName,
				TriggerCount:     strategyInfo.TriggerCount,
				Priority:         strategyInfo.Priority,
				Scope:            strategyInfo.Scope,
				Action:           strategyInfo.Action,
				Description:      strategyInfo.Description,
			},
			Status:    strategyInfo.Status,
			CreatedAt: strategyInfo.CreatedAt,
			UpdatedAt: strategyInfo.UpdatedAt,
		})
	}

	ginx.SuccessJSONResponse(c, ginx.NewPaginatedRespData(count, output))
}

// Get gets a strategy
//
//	@ID			openapi_strategy_get
//	@Summary	strategy get
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id			path		int	true	"strategy id"
//	@Param		bk_biz_id	query		int	true	"bk_biz_id"
//	@Success	200			{object}	serializer.StrategyOutputInfo
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
		StrategyInfo: serializer.StrategyInfo{
			ID:               strategyInfo.ID,
			Name:             strategyInfo.Name,
			BkBizID:          strategyInfo.BkBizID,
			TriggerEventName: strategyInfo.TriggerEventName,
			TriggerCount:     strategyInfo.TriggerCount,
			Priority:         strategyInfo.Priority,
			Scope:            strategyInfo.Scope,
			Action:           strategyInfo.Action,
			Description:      strategyInfo.Description,
		},
		Status:    strategyInfo.Status,
		CreatedAt: strategyInfo.CreatedAt,
		UpdatedAt: strategyInfo.UpdatedAt,
	}

	ginx.SuccessJSONResponse(c, output)
}

// Update updates a strategy
//
//	@ID			openapi_strategy_update
//	@Summary	strategy update
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id		path	int									true	"strategy id"
//	@Param		request	body	serializer.StrategyUpdateRequest	true	"strategy update request"
//	@Success	204
//	@Router		/api/admin/strategies/{id}/ [put]
func (h *StrategyHandler) Update(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	var req serializer.StrategyUpdateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, req.BkBizID)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	isDuplicated, err := serializer.CheckDuplicatedName(h.strategyService, pathParam.ID, req.BkBizID, req.Name)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	strategyInfo := &hamodel.DbSwitchingStrategy{
		ID:               pathParam.ID,
		Name:             req.Name,
		BkBizID:          req.BkBizID,
		TriggerEventName: req.TriggerEventName,
		TriggerCount:     req.TriggerCount,
		Priority:         req.Priority,
		Scope:            req.Scope,
		Action:           req.Action,
		Description:      req.Description,
	}

	if err := h.strategyService.UpdateStrategy(strategyInfo); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// Delete deletes a strategy
//
//	@ID			openapi_strategy_delete
//	@Summary	strategy delete
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id			path	int	true	"strategy id"
//	@Param		bk_biz_id	query	int	true	"bk_biz_id"
//	@Success	204
//	@Router		/api/admin/strategies/{id}/ [delete]
func (h *StrategyHandler) Delete(c *gin.Context) {
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

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, req.BkBizID)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	if err := h.strategyService.UpdateStrategyStatus(pathParam.ID, req.BkBizID, hamodel.StatusTypeDeleted); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// StatusUpdate updates a strategy status
//
//	@ID			openapi_strategy_status_update
//	@Summary	strategy status update
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id		path	int										true	"strategy id"
//	@Param		request	body	serializer.StrategyStatusUpdateRequest	true	"strategy status update request"
//	@Success	204
//	@Router		/api/admin/strategies/{id}/status/ [put]
func (h *StrategyHandler) StatusUpdate(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	var req serializer.StrategyStatusUpdateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, req.BkBizID)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	if err := h.strategyService.UpdateStrategyStatus(pathParam.ID, req.BkBizID, req.Status); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// GlobalList global strategies list
//
//	@ID			openapi_global_strategy_list
//	@Summary	global strategy list
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	query		serializer.GlobalStrategyListRequest	false	"query parameters"
//	@Success	200		{object}	ginx.PaginatedResponse{results=serializer.StrategyListResponse}
//	@Router		/api/admin/global/strategies/ [get]
func (h *StrategyHandler) GlobalList(c *gin.Context) {
	var req serializer.GlobalStrategyListRequest
	if err := c.ShouldBind(&req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	strategies, count, err := h.strategyService.ListStrategies(
		0,
		req.Name,
		req.Scope,
		req.Action,
		req.Status,
		ginx.GetOffset(c),
		ginx.GetLimit(c),
	)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	var output serializer.StrategyListResponse

	for _, strategyInfo := range strategies {
		output = append(output, serializer.StrategyOutputInfo{
			StrategyInfo: serializer.StrategyInfo{
				ID:               strategyInfo.ID,
				Name:             strategyInfo.Name,
				BkBizID:          strategyInfo.BkBizID,
				TriggerEventName: strategyInfo.TriggerEventName,
				TriggerCount:     strategyInfo.TriggerCount,
				Priority:         strategyInfo.Priority,
				Scope:            strategyInfo.Scope,
				Action:           strategyInfo.Action,
				Description:      strategyInfo.Description,
			},
			Status:    strategyInfo.Status,
			CreatedAt: strategyInfo.CreatedAt,
			UpdatedAt: strategyInfo.UpdatedAt,
		})
	}

	ginx.SuccessJSONResponse(c, ginx.NewPaginatedRespData(count, output))
}

// GlobalCreate creates a global strategy
//
//	@ID			openapi_global_strategy_create
//	@Summary	global strategy create
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		request	body	serializer.GlobalStrategyCreateRequest	true	"strategy create request"
//	@Success	201
//	@Router		/api/admin/global/strategies/ [post]
func (h *StrategyHandler) GlobalCreate(c *gin.Context) {
	var req serializer.GlobalStrategyCreateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	isDuplicated, err := serializer.CheckDuplicatedName(h.strategyService, 0, 0, req.Name)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	strategyInfo := &hamodel.DbSwitchingStrategy{
		Name:             req.Name,
		BkBizID:          0,
		TriggerEventName: req.TriggerEventName,
		TriggerCount:     req.TriggerCount,
		Priority:         req.Priority,
		Scope:            req.Scope,
		Action:           req.Action,
		Description:      req.Description,
		Status:           hamodel.StatusTypeEnabled,
	}

	if err := h.strategyService.CreateStrategy(strategyInfo); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessCreateResponse(c)
}

// GlobalGet gets a global strategy
//
//	@ID			openapi_global_strategy_get
//	@Summary	global strategy get
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id	path		int	true	"strategy id"
//	@Success	200	{object}	serializer.StrategyOutputInfo
//	@Router		/api/admin/global/strategies/{id}/ [get]
func (h *StrategyHandler) GlobalGet(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	strategyInfo, err := h.strategyService.GetStrategy(pathParam.ID, 0)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	if strategyInfo == nil || strategyInfo.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	output := serializer.StrategyOutputInfo{
		StrategyInfo: serializer.StrategyInfo{
			ID:               strategyInfo.ID,
			Name:             strategyInfo.Name,
			BkBizID:          strategyInfo.BkBizID,
			TriggerEventName: strategyInfo.TriggerEventName,
			TriggerCount:     strategyInfo.TriggerCount,
			Priority:         strategyInfo.Priority,
			Scope:            strategyInfo.Scope,
			Action:           strategyInfo.Action,
			Description:      strategyInfo.Description,
		},
		Status:    strategyInfo.Status,
		CreatedAt: strategyInfo.CreatedAt,
		UpdatedAt: strategyInfo.UpdatedAt,
	}

	ginx.SuccessJSONResponse(c, output)
}

// GlobalUpdate updates a global strategy
//
//	@ID			openapi_global_strategy_update
//	@Summary	global strategy update
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id		path	int										true	"strategy id"
//	@Param		request	body	serializer.GlobalStrategyUpdateRequest	true	"strategy update request"
//	@Success	204
//	@Router		/api/admin/global/strategies/{id}/ [put]
func (h *StrategyHandler) GlobalUpdate(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	var req serializer.GlobalStrategyUpdateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, 0)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	isDuplicated, err := serializer.CheckDuplicatedName(h.strategyService, pathParam.ID, 0, req.Name)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if isDuplicated {
		ginx.BadRequestErrorJSONResponse(c, ginx.ErrStrategyNameExists)
		return
	}

	strategyInfo := &hamodel.DbSwitchingStrategy{
		ID:               pathParam.ID,
		Name:             req.Name,
		BkBizID:          0,
		TriggerEventName: req.TriggerEventName,
		TriggerCount:     req.TriggerCount,
		Priority:         req.Priority,
		Scope:            req.Scope,
		Action:           req.Action,
		Description:      req.Description,
	}

	if err := h.strategyService.UpdateStrategy(strategyInfo); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// GlobalDelete deletes a global strategy
//
//	@ID			openapi_global_strategy_delete
//	@Summary	global strategy delete
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id	path	int	true	"strategy id"
//	@Success	204
//	@Router		/api/admin/global/strategies/{id}/ [delete]
func (h *StrategyHandler) GlobalDelete(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, 0)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	if err := h.strategyService.UpdateStrategyStatus(pathParam.ID, 0, hamodel.StatusTypeDeleted); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}

// GlobalStatusUpdate updates a global strategy status
//
//	@ID			openapi_global_strategy_status_update
//	@Summary	global strategy status update
//	@Accept		json
//	@Produce	json
//	@Tags		openapi.strategy
//	@Param		id		path	int												true	"strategy id"
//	@Param		request	body	serializer.GlobalStrategyStatusUpdateRequest	true	"strategy status update request"
//	@Success	204
//	@Router		/api/admin/global/strategies/{id}/status/ [put]
func (h *StrategyHandler) GlobalStatusUpdate(c *gin.Context) {
	var pathParam serializer.StrategyPathParam
	if err := c.ShouldBindUri(&pathParam); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	var req serializer.GlobalStrategyStatusUpdateRequest
	if err := hanet.BindAndValidate(c, &req); err != nil {
		ginx.BadRequestErrorJSONResponse(c, err)
		return
	}

	existingStrategy, err := h.strategyService.GetStrategy(pathParam.ID, 0)
	if err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}
	if existingStrategy == nil || existingStrategy.ID == 0 {
		ginx.NotFoundJSONResponse(c, ginx.ErrStrategyNotFound)
		return
	}

	if err := h.strategyService.UpdateStrategyStatus(pathParam.ID, 0, req.Status); err != nil {
		ginx.SystemErrorJSONResponse(c, err)
		return
	}

	ginx.SuccessNoContentResponse(c)
}
