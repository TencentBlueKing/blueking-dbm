/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	coreentity "k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	commentity "k8s-dbs/common/entity"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	"k8s-dbs/metadata/provider"
	metareq "k8s-dbs/metadata/vo/request"
	metaresp "k8s-dbs/metadata/vo/response"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// ComponentSpecPlanController manages component spec plans.
type ComponentSpecPlanController struct {
	componentSpecPlanProvider provider.ComponentSpecPlanProvider
}

// NewComponentSpecPlanController creates a new instance of ComponentSpecPlanController.
func NewComponentSpecPlanController(
	componentSpecPlanProvider provider.ComponentSpecPlanProvider,
) *ComponentSpecPlanController {
	return &ComponentSpecPlanController{componentSpecPlanProvider}
}

// ListComponentSpecPlans 获取 component spec plan 列表
func (c *ComponentSpecPlanController) ListComponentSpecPlans(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaComponentSpecPlanList)
	var params metaentity.ComponentSpecPlanQueryParams
	if err := ctx.ShouldBindQuery(&params); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	specPlanEntities, err := c.componentSpecPlanProvider.FindSpecPlanByParams(&params)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []metaresp.ComponentSpecPlanResponse
	if err := copier.Copy(&data, specPlanEntities); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// GetComponentSpecPlan 获取 component spec plan 详情
func (c *ComponentSpecPlanController) GetComponentSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaComponentSpecPlanDetail)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	specPlanEntity, err := c.componentSpecPlanProvider.FindSpecPlanByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data metaresp.ComponentSpecPlanResponse
	if err := copier.Copy(&data, specPlanEntity); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateComponentSpecPlan 创建 component spec plan
func (c *ComponentSpecPlanController) CreateComponentSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaComponentSpecPlanCreate)
	var req metareq.ComponentSpecPlanRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var entity metaentity.ComponentSpecPlanEntity
	if err := copier.Copy(&entity, &req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAdditional: &req.BKAdditional,
	}
	addedSpecPlan, err := c.componentSpecPlanProvider.CreateSpecPlan(&dbsCtx, &entity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data metaresp.ComponentSpecPlanResponse
	if err := copier.Copy(&data, addedSpecPlan); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateComponentSpecPlan 更新 component spec plan
func (c *ComponentSpecPlanController) UpdateComponentSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaComponentSpecPlanUpdate)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var req metareq.ComponentSpecPlanRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var entity metaentity.ComponentSpecPlanEntity
	if err := copier.Copy(&entity, &req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAdditional: &req.BKAdditional,
	}
	entity.ID = id
	rows, err := c.componentSpecPlanProvider.UpdateSpecPlan(&dbsCtx, &entity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteComponentSpecPlan 删除 component spec plan
func (c *ComponentSpecPlanController) DeleteComponentSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaComponentSpecPlanDelete)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	rows, err := c.componentSpecPlanProvider.DeleteSpecPlanByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
