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
	commentity "k8s-dbs/common/entity"
	coreapiconst "k8s-dbs/core/constant"
	"k8s-dbs/core/entity"
	"k8s-dbs/core/provider"
	reqvo "k8s-dbs/core/vo/request"
	"k8s-dbs/errors"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/copier"
)

// AddonController  addon controller
type AddonController struct {
	addonProvider *provider.AddonProvider
}

// InstallAddon 安装 addon 插件
func (a *AddonController) InstallAddon(ctx *gin.Context) {
	var installReqVo reqvo.AddonOperationRequest
	if err := ctx.ShouldBindJSON(&installReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, &installReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	dbsContext := commentity.DbsContext{}
	dbsContext.BkAuth = &installReqVo.BKAuth
	err := a.addonProvider.ManageAddon(&dbsContext, &addonEntity, coreapiconst.InstallAddonOP)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// UninstallAddon 卸载 addon 插件
func (a *AddonController) UninstallAddon(ctx *gin.Context) {
	var uninstallReqVo reqvo.AddonOperationRequest
	if err := ctx.ShouldBindJSON(&uninstallReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, &uninstallReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &uninstallReqVo.BKAuth,
	}
	err := a.addonProvider.ManageAddon(&dbsContext, &addonEntity, coreapiconst.UninstallAddonOP)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// UpgradeAddon 更新 addon 插件
func (a *AddonController) UpgradeAddon(ctx *gin.Context) {
	var upgradeReqVo reqvo.AddonOperationRequest
	if err := ctx.ShouldBindJSON(&upgradeReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, &upgradeReqVo); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeAddonError, err))
		return
	}
	dbsContext := commentity.DbsContext{
		BkAuth: &upgradeReqVo.BKAuth,
	}
	err := a.addonProvider.ManageAddon(&dbsContext, &addonEntity, coreapiconst.UpgradeAddonOP)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeAddonError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// NewAddonController 构建 AddonController
func NewAddonController(addonProvider *provider.AddonProvider) *AddonController {
	return &AddonController{
		addonProvider,
	}
}
