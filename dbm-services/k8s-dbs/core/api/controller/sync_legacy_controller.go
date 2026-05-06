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
	"log/slog"

	"github.com/gin-gonic/gin"

	"k8s-dbs/common/api"
	"k8s-dbs/core/provider"
	dbserrors "k8s-dbs/errors"
)

// SyncLegacyController 存量集群同步 Controller
type SyncLegacyController struct {
	syncLegacyProvider *provider.SyncLegacyProvider
}

// NewSyncLegacyController 创建 SyncLegacyController 实例
func NewSyncLegacyController(syncLegacyProvider *provider.SyncLegacyProvider) *SyncLegacyController {
	return &SyncLegacyController{
		syncLegacyProvider: syncLegacyProvider,
	}
}

// SyncLegacyClusters 将存量集群批量同步到 DBM
func (c *SyncLegacyController) SyncLegacyClusters(ctx *gin.Context) {
	slog.Info("开始执行存量集群同步到 DBM")

	result, err := c.syncLegacyProvider.SyncLegacyClusters()
	if err != nil {
		slog.Error("存量集群同步失败", "error", err)
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ServerError, err))
		return
	}

	api.SuccessResponse(ctx, result, "存量集群同步完成")
}

// SyncFilteredClusters 按过滤条件将指定集群同步到 DBM
func (c *SyncLegacyController) SyncFilteredClusters(ctx *gin.Context) {
	var req provider.SyncFilteredRequest
	if err := ctx.ShouldBindJSON(&req); err != nil {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError, err))
		return
	}

	if len(req.ClusterNames) > 0 && req.Namespace == "" {
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ParameterInvalidError,
			fmt.Errorf("指定 clusterNames 时必须同时指定 namespace，避免跨命名空间匹配到同名集群")))
		return
	}

	slog.Info("开始执行按条件同步集群到 DBM",
		"k8sClusterName", req.K8sClusterName,
		"namespace", req.Namespace,
		"clusterNames", req.ClusterNames)

	result, err := c.syncLegacyProvider.SyncFilteredClusters(&req)
	if err != nil {
		slog.Error("按条件同步集群失败", "error", err)
		api.ErrorResponse(ctx, dbserrors.NewK8sDbsError(dbserrors.ServerError, err))
		return
	}

	api.SuccessResponse(ctx, result, "按条件同步集群完成")
}
