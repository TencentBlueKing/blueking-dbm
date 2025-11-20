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
	request := &reqvo.AddonOperationRequest{}
	a.setAPIRequestContext(ctx, request, commconst.APIAddonInstall)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAuth:           &request.BKAuth,
		K8sClusterName:   addonEntity.K8sClusterName,
		RequestType:      string(coreapiconst.InstallAddonOP),
		APIRequestParams: request,
	}

	err := a.addonProvider.ManageAddon(&dbsCtx, &addonEntity, coreapiconst.InstallAddonOP)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.InstallAddonError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// UninstallAddon 卸载 addon 插件
func (a *AddonController) UninstallAddon(ctx *gin.Context) {
	request := &reqvo.AddonOperationRequest{}
	a.setAPIRequestContext(ctx, request, commconst.APIAddonUninstall)

	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAuth:           &request.BKAuth,
		K8sClusterName:   addonEntity.K8sClusterName,
		RequestType:      string(coreapiconst.UninstallAddonOP),
		APIRequestParams: request,
	}
	err := a.addonProvider.ManageAddon(&dbsCtx, &addonEntity, coreapiconst.UninstallAddonOP)
	if err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UninstallAddonError, err))
		return
	}
	api.SuccessResponse(ctx, nil, commconst.Success)
}

// UpgradeAddon 更新 addon 插件
func (a *AddonController) UpgradeAddon(ctx *gin.Context) {
	request := &reqvo.AddonOperationRequest{}
	a.setAPIRequestContext(ctx, request, commconst.APIAddonUpgrade)
	if err := ctx.ShouldBindJSON(request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeAddonError, err))
		return
	}
	var addonEntity entity.AddonEntity
	if err := copier.Copy(&addonEntity, request); err != nil {
		api.ErrorResponse(ctx, errors.NewK8sDbsError(errors.UpgradeAddonError, err))
		return
	}
	dbsCtx := commentity.DbsContext{
		BkAuth:           &request.BKAuth,
		K8sClusterName:   addonEntity.K8sClusterName,
		RequestType:      string(coreapiconst.UpgradeAddonOP),
		APIRequestParams: request,
	}
	err := a.addonProvider.ManageAddon(&dbsCtx, &addonEntity, coreapiconst.UpgradeAddonOP)
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

// setAPIRequestContext 设置 api 请求上下文
func (a *AddonController) setAPIRequestContext(
	ctx *gin.Context,
	request *reqvo.AddonOperationRequest,
	apiName string,
) {
	ctx.Set(commconst.APIName, apiName)
	ctx.Set(commconst.APIRequestEntity, request)
}
