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
	commconst "k8s-dbs/common/api/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/metadata/api/vo/resp"
	"k8s-dbs/metadata/provider"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// K8sClusterAddonsController manages metadata for addons.
type K8sClusterAddonsController struct {
	caProvider provider.K8sClusterAddonsProvider
}

// NewK8sClusterAddonsController creates a new instance of K8sClusterAddonsController.
func NewK8sClusterAddonsController(caProvider provider.K8sClusterAddonsProvider) *K8sClusterAddonsController {
	return &K8sClusterAddonsController{caProvider}
}

// GetAddon retrieves a cluster addon by its ID.
func (k *K8sClusterAddonsController) GetAddon(ctx *gin.Context) {
	idParam := ctx.Param("id")
	id, err := strconv.ParseUint(idParam, 10, 64)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	addon, err := k.caProvider.FindClusterAddonByID(id)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data resp.K8sClusterAddonsRespVo
	if err := copier.Copy(&data, addon); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}

// GetAddonsByClusterName retrieves cluster addons by k8s_cluster_name.
func (k *K8sClusterAddonsController) GetAddonsByClusterName(ctx *gin.Context) {
	k8sClusterName := ctx.Query("k8sClusterName")
	params := map[string]interface{}{
		"k8s_cluster_name": k8sClusterName,
	}
	clusterAddons, err := k.caProvider.FindClusterAddonByParams(params)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	var data []resp.K8sClusterAddonsRespVo
	if err := copier.Copy(&data, clusterAddons); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.GetMetaDataErr, err))
		return
	}
	entity.SuccessResponse(ctx, data, commconst.Success)
}
