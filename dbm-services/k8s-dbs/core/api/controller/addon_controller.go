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
	coreconst "k8s-dbs/core/api/constants"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/errors"
	"k8s-dbs/core/provider"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"

	reqvo "k8s-dbs/core/api/vo/req"

	pventity "k8s-dbs/core/provider/entity"
)

// AddonController  插件管理 controller
type AddonController struct {
	addonProvider *provider.AddonProvider
}

// DeployAddon 安装 addon 插件
func (k *AddonController) DeployAddon(ctx *gin.Context) {
	var addonDeployReqVo reqvo.AddonDeployReqVo
	if err := ctx.ShouldBindJSON(&addonDeployReqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeployAddonError, err))
		return
	}
	var addonEntity pventity.AddonEntity
	if err := copier.Copy(&addonEntity, &addonDeployReqVo); err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeployAddonError, err))
		return
	}
	err := k.addonProvider.DeployAddon(&addonEntity)
	if err != nil {
		entity.ErrorResponse(ctx, errors.NewGlobalError(errors.DeployAddonError, err))
		return
	}
	entity.SuccessResponse(ctx, nil, coreconst.Success)
}

// NewAddonController 构建 AddonProvider
func NewAddonController(addonProvider *provider.AddonProvider) *AddonController {
	return &AddonController{
		addonProvider,
	}
}
