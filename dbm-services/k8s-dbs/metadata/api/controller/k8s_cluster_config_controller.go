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
	"fmt"
	commconst "k8s-dbs/common/api/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/req"
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"
	entitys "k8s-dbs/metadata/provider/entity"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// K8sClusterConfigController manages the metadata for k8s-cluster.
type K8sClusterConfigController struct {
	configProvider provider.K8sClusterConfigProvider
}

// NewK8sClusterConfigController create a new instance of K8sClusterConfigController.
func NewK8sClusterConfigController(configProvider provider.K8sClusterConfigProvider) *K8sClusterConfigController {
	return &K8sClusterConfigController{configProvider}
}

// GetK8sClusterConfigByID get clusterConfig by its ID.
func (k *K8sClusterConfigController) GetK8sClusterConfigByID(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	config, err := k.configProvider.FindConfigByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var respVo resp.K8sClusterConfigRespVo
	if err := copier.Copy(&respVo, config); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}

// GetK8sClusterConfigByName get clusterConfig by its Name.
func (k *K8sClusterConfigController) GetK8sClusterConfigByName(ctx *gin.Context) {
	nameParam := ctx.Param("cluster_name")
	if nameParam == "" {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, fmt.Errorf("cluster_name 参数不能为空")))
		return
	}
	config, err := k.configProvider.FindConfigByName(nameParam)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var respVo resp.K8sClusterConfigRespVo
	if err := copier.Copy(&respVo, config); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}

// CreateK8sClusterConfig create a new clusterConfig.
func (k *K8sClusterConfigController) CreateK8sClusterConfig(ctx *gin.Context) {
	var reqVo req.K8sClusterConfigReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var configEntity entitys.K8sClusterConfigEntity
	if err := copier.Copy(&configEntity, &reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	addedConfig, err := k.configProvider.CreateConfig(&configEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	var respVo resp.K8sClusterConfigRespVo
	if err := copier.Copy(&respVo, addedConfig); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.CreateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, respVo, commconst.Success)
}

// UpdateK8sClusterConfig update existing clusterConfig.
func (k *K8sClusterConfigController) UpdateK8sClusterConfig(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var reqVo req.K8sClusterConfigReqVo
	if err := ctx.ShouldBindJSON(&reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	var configEntity entitys.K8sClusterConfigEntity
	if err := copier.Copy(&configEntity, reqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	configEntity.ID = id
	rows, err := k.configProvider.UpdateConfig(&configEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.UpdateMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}

// DeleteK8sClusterConfig delete a clusterConfig by its ID.
func (k *K8sClusterConfigController) DeleteK8sClusterConfig(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	rows, err := k.configProvider.DeleteConfigByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeleteMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, map[string]uint64{"rows": rows}, commconst.Success)
}
