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
	coreconst "k8s-dbs/common/constant"
	"k8s-dbs/core/provider"
	"k8s-dbs/errors"
	"log/slog"

	webreq "k8s-dbs/dataweb/vo/request"

	"github.com/gin-gonic/gin"
)

// ClusterController 存储集群管理 Controller
type ClusterController struct {
	clusterProvider *provider.ClusterProvider
}

// NewClusterController 创建 ClusterController 实例
func NewClusterController(
	clusterProvider *provider.ClusterProvider,
) *ClusterController {
	return &ClusterController{
		clusterProvider: clusterProvider,
	}
}

// CreateCluster 创建集群
func (c *ClusterController) CreateCluster(ctx *gin.Context) {
	clusterInstall := &webreq.ClusterInstallRequest{}
	if err := ctx.BindJSON(&clusterInstall); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	clusterConfig, err := ClusterConfBuilderFactory.
		GetBuilder(clusterInstall.BasicInfo.StorageAddonType).
		BuildConfig(clusterInstall)
	if err != nil {
		slog.Error("convert to cluster config error", "clusterInstall", clusterInstall, "err", err)
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	if err := c.clusterProvider.CreateCluster(clusterConfig); err != nil {
		coreentity.ErrorResponse(ctx, errors.NewK8sDbsError(errors.CreateClusterError, err))
		return
	}
	coreentity.SuccessResponse(ctx, nil, coreconst.Success)
}
