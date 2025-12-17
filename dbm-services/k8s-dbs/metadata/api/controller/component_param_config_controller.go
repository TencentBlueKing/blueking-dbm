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
	"k8s-dbs/common/api"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metamodel "k8s-dbs/metadata/model"
	"k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/vo/request"
	"k8s-dbs/metadata/vo/response"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonParamConfigDbAccess 数据库访问接口（用于 Controller）
type AddonParamConfigDbAccess interface {
	Create(model *metamodel.AddonParamConfigModel) (*metamodel.AddonParamConfigModel, error)
	BatchCreate(models []*metamodel.AddonParamConfigModel) error
	DeleteByID(id uint64) (uint64, error)
	Update(model *metamodel.AddonParamConfigModel) (uint64, error)
}

// AddonParamConfigController 组件参数配置控制器
type AddonParamConfigController struct {
	provider provider.AddonParamConfigProvider
	dbAccess AddonParamConfigDbAccess
}

// NewAddonParamConfigController 创建控制器实例
func NewAddonParamConfigController(
	p provider.AddonParamConfigProvider,
	dbAccess AddonParamConfigDbAccess,
) *AddonParamConfigController {
	return &AddonParamConfigController{provider: p, dbAccess: dbAccess}
}

// List 查询参数配置列表
func (c *AddonParamConfigController) List(ctx *gin.Context) {
	ctx.Set(commconst.APIName, "component_param_config_list")

	var params metaentity.AddonParamConfigQueryParams

	// 从查询参数获取过滤条件
	if addonIDStr := ctx.Query("addonId"); addonIDStr != "" {
		if addonID, err := strconv.ParseUint(addonIDStr, 10, 64); err == nil {
			params.AddonID = addonID
		}
	}
	params.ServiceVersion = ctx.Query("serviceVersion")
	params.ComponentName = ctx.Query("componentName")

	configs, err := c.provider.FindByParams(&params)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}

	var respList []response.AddonParamConfigResponse
	if err = copier.Copy(&respList, configs); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.GetMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, respList, commconst.Success)
}

// Create 创建单条参数配置
func (c *AddonParamConfigController) Create(ctx *gin.Context) {
	ctx.Set(commconst.APIName, "component_param_config_create")

	var reqVo request.AddonParamConfigRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	model := &metamodel.AddonParamConfigModel{
		AddonID:        reqVo.AddonID,
		ServiceVersion: reqVo.ServiceVersion,
		ComponentName:  reqVo.ComponentName,
		ParamName:      reqVo.ParamName,
		ParamType:      reqVo.ParamType,
		DefaultValue:   reqVo.DefaultValue,
		Active:         true,
	}

	added, err := c.dbAccess.Create(model)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}

	var resp response.AddonParamConfigResponse
	if err = copier.Copy(&resp, added); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, resp, commconst.Success)
}

// BatchCreate 批量创建参数配置
func (c *AddonParamConfigController) BatchCreate(ctx *gin.Context) {
	ctx.Set(commconst.APIName, "component_param_config_batch_create")

	var reqList []request.AddonParamConfigRequest
	if err := ctx.ShouldBindJSON(&reqList); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	var models []*metamodel.AddonParamConfigModel
	for _, req := range reqList {
		model := &metamodel.AddonParamConfigModel{
			AddonID:        req.AddonID,
			ServiceVersion: req.ServiceVersion,
			ComponentName:  req.ComponentName,
			ParamName:      req.ParamName,
			ParamType:      req.ParamType,
			DefaultValue:   req.DefaultValue,
			Active:         true,
		}
		models = append(models, model)
	}

	if err := c.dbAccess.BatchCreate(models); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, gin.H{"count": len(models)}, commconst.Success)
}

// Delete 删除参数配置
func (c *AddonParamConfigController) Delete(ctx *gin.Context) {
	ctx.Set(commconst.APIName, "component_param_config_delete")

	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	if _, err := c.dbAccess.DeleteByID(id); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.DeleteMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, nil, commconst.Success)
}

// Update 更新参数配置
func (c *AddonParamConfigController) Update(ctx *gin.Context) {
	ctx.Set(commconst.APIName, "component_param_config_update")

	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	var reqVo request.AddonParamConfigRequest
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.ParameterInvalidError, err))
		return
	}

	model := &metamodel.AddonParamConfigModel{
		ID:             id,
		AddonID:        reqVo.AddonID,
		ServiceVersion: reqVo.ServiceVersion,
		ComponentName:  reqVo.ComponentName,
		ParamName:      reqVo.ParamName,
		ParamType:      reqVo.ParamType,
		DefaultValue:   reqVo.DefaultValue,
		Active:         true,
	}

	if _, err := c.dbAccess.Update(model); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}

	var resp response.AddonParamConfigResponse
	if err = copier.Copy(&resp, model); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpdateMetaDataError, err))
		return
	}

	api.SuccessResponse(ctx, resp, commconst.Success)
}
