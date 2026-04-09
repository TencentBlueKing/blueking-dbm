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

// AddonSpecPlanController manages addon spec plans.
type AddonSpecPlanController struct {
	addonSpecPlanProvider provider.AddonSpecPlanProvider
}

// NewAddonSpecPlanController creates a new instance of AddonSpecPlanController.
func NewAddonSpecPlanController(
	addonSpecPlanProvider provider.AddonSpecPlanProvider,
) *AddonSpecPlanController {
	return &AddonSpecPlanController{
		addonSpecPlanProvider: addonSpecPlanProvider,
	}
}

// ListAddonSpecPlans 获取 addon spec plan 列表
func (a *AddonSpecPlanController) ListAddonSpecPlans(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaAddonSpecPlanList)
	var params metaentity.AddonSpecPlanQueryParams
	if err := ctx.ShouldBindQuery(&params); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	specPlanEntities, err := a.addonSpecPlanProvider.FindSpecPlanByParams(&params)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	var data []metaresp.AddonSpecPlanResponse
	if err := copier.Copy(&data, specPlanEntities); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// GetAddonSpecPlan 获取 addon spec plan 详情列表（含关联的组件套餐信息）
func (a *AddonSpecPlanController) GetAddonSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaAddonSpecPlanDetail)
	var req metareq.GetAddonSpecPlanRequest
	if err := ctx.ShouldBindQuery(&req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	detailEntities, err := a.addonSpecPlanProvider.FindSpecPlanDetails(&metaentity.AddonSpecPlanDetailQueryParams{
		AddonType:     req.AddonType,
		AddonVersion:  req.AddonVersion,
		AddonTopology: req.AddonTopology,
	})
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	if len(detailEntities) == 0 {
		coreentity.SuccessResponse(ctx, nil, commconst.Success)
		return
	}
	var data []metaresp.AddonSpecPlanDetailResponse
	if err := copier.Copy(&data, &detailEntities); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// CreateAddonSpecPlan 创建 addon spec plan
func (a *AddonSpecPlanController) CreateAddonSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaAddonSpecPlanCreate)
	var req metareq.AddonSpecPlanRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var entity metaentity.AddonSpecPlanEntity
	if err := copier.Copy(&entity, &req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAdditional: &req.BKAdditional,
	}
	addedSpecPlan, err := a.addonSpecPlanProvider.CreateSpecPlan(&dbsCtx, &entity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	var data metaresp.AddonSpecPlanResponse
	if err := copier.Copy(&data, addedSpecPlan); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, data, commconst.Success)
}

// UpdateAddonSpecPlan 更新 addon spec plan
func (a *AddonSpecPlanController) UpdateAddonSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaAddonSpecPlanUpdate)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var req metareq.AddonSpecPlanRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	var entity metaentity.AddonSpecPlanEntity
	if err := copier.Copy(&entity, &req); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAdditional: &req.BKAdditional,
	}
	entity.ID = id
	rows, err := a.addonSpecPlanProvider.UpdateSpecPlan(&dbsCtx, &entity)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteAddonSpecPlan 删除 addon spec plan
func (a *AddonSpecPlanController) DeleteAddonSpecPlan(ctx *gin.Context) {
	ctx.Set(commconst.APIName, commconst.APIMetaAddonSpecPlanDelete)
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	rows, err := a.addonSpecPlanProvider.DeleteSpecPlanByID(id)
	if err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}
	coreentity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
