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

package util

import (
	"context"
	"fmt"
	coreconst "k8s-dbs/core/constant"
	infreq "k8s-dbs/infrastructure/request"
	infresp "k8s-dbs/infrastructure/response"
	"k8s-dbs/infrastructure/thirdapi"
	metaentity "k8s-dbs/metadata/entity"
	"log/slog"
	"time"

	"github.com/pkg/errors"
	"golang.org/x/sync/errgroup"
)

// clusterTypeMap 存储插件类型到DBM集群类型的映射表
var clusterTypeMap = map[string]string{
	string(coreconst.Victoriametrics): "k8s_vm",
	string(coreconst.Greptimedb):      "k8s_gt",
	string(coreconst.Surreal):         "k8s_surreal",
	string(coreconst.Risingwave):      "k8s_rw",
	string(coreconst.Milvus):          "k8s_mv",
}

// GetDbmClusterType 获取对应的 dbm cluster type
func GetDbmClusterType(storageAddonType string) (string, error) {
	if clusterType, exists := clusterTypeMap[storageAddonType]; exists {
		return clusterType, nil
	}

	return "", fmt.Errorf("不支持的存储插件类型: %s", storageAddonType)
}

// AsyncClusterCreated 同步集群创建信息到DBM
func AsyncClusterCreated(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群创建信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationCreate, dbmAPIService, syncClusterCreatedWithCtx)
}

// AsyncClusterUpdated 同步集群更新信息到DBM
func AsyncClusterUpdated(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群更新信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationUpdate, dbmAPIService, syncClusterNormalWithCtx)
}

// AsyncClusterDeleted 同步集群删除信息到DBM
func AsyncClusterDeleted(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群删除信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationDelete, dbmAPIService, syncClusterDeletedWithCtx)
}

// AsyncClusterExposed 同步集群服务暴露信息到DBM
func AsyncClusterExposed(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群暴露信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationExpose, dbmAPIService, syncClusterExposedWithCtx)
}

// AsyncClusterStopped 同步集群停止信息到DBM
func AsyncClusterStopped(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群停止信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationStop, dbmAPIService, syncClusterStoppedWithCtx)
}

// AsyncClusterStarted 同步集群启动信息到DBM
func AsyncClusterStarted(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群启动信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationStart, dbmAPIService, syncClusterStartedWithCtx)
}

// AsyncClusterRestarted 同步集群重启信息到DBM
func AsyncClusterRestarted(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群重启信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationRestart, dbmAPIService, syncClusterRestartedWithCtx)
}

// AsyncClusterHScaled 同步集群水平扩缩信息到DBM
func AsyncClusterHScaled(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群水平扩缩信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationHscaling, dbmAPIService, syncClusterHsWithCtx)
}

// AsyncClusterVScaled 同步集群垂直扩缩信息到DBM
func AsyncClusterVScaled(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群垂直扩缩信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationVscaling, dbmAPIService, syncClusterVsWithCtx)
}

// AsyncClusterVolumeExpanded 同步集群磁盘扩缩信息到DBM
func AsyncClusterVolumeExpanded(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群磁盘扩缩信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationVolumeExpand, dbmAPIService, syncClusterVeWithCtx)
}

// AsyncClusterAbnormal 同步集群异常状态信息到DBM
func AsyncClusterAbnormal(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群异常状态信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationStatusAbnormal, dbmAPIService, syncClusterAbnormalWithCtx)
}

// AsyncClusterNormal 同步集群正常状态信息到DBM
func AsyncClusterNormal(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群正常状态信息", "cluster_name", clusterEntity.ClusterName)
	asyncClusterOperation(clusterEntity, coreconst.OperationStatusNormal, dbmAPIService, syncClusterNormalWithCtx)
}

// asyncClusterOperation 通用的异步集群操作函数，支持创建、更新和删除操作
func asyncClusterOperation(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	operationType coreconst.ClusterOperationType,
	dbmAPIService *thirdapi.DbmAPIService,
	syncFunc func(context.Context, *metaentity.K8sCrdClusterEntity, *thirdapi.DbmAPIService) error,
) {
	// 创建带超时的context，避免异步任务无限期运行
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)

	// 使用errgroup管理异步任务
	g := &errgroup.Group{}

	// 启动异步同步任务
	g.Go(func() error {
		return syncFunc(ctx, clusterEntity, dbmAPIService)
	})

	// 在单独的goroutine中等待任务完成并处理结果
	go func() {
		// 确保在goroutine结束时取消context
		defer cancel()

		// 等待所有任务完成
		err := g.Wait()

		if err != nil {
			if errors.Is(err, context.DeadlineExceeded) {
				slog.Warn("同步集群"+string(operationType)+"信息超时",
					"cluster_name", clusterEntity.ClusterName,
					"namespace", clusterEntity.Namespace,
					"timeout", "30s",
				)
			} else {
				slog.Error("同步集群"+string(operationType)+"信息失败",
					"cluster_name", clusterEntity.ClusterName,
					"namespace", clusterEntity.Namespace,
					"error", err,
				)
			}
		} else {
			slog.Info("同步集群"+string(operationType)+"信息成功",
				"cluster_name", clusterEntity.ClusterName,
				"namespace", clusterEntity.Namespace,
			)
		}
	}()
}

// syncClusterExposedWithCtx 带context的同步集群暴露信息到DBM
func syncClusterExposedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationExpose)
}

// syncClusterStoppedWithCtx 带context的同步集群停止信息到DBM
func syncClusterStoppedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationStop)
}

// syncClusterStartedWithCtx 带context的同步集群启动信息到DBM
func syncClusterStartedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationStart)
}

// syncClusterRestartedWithCtx 带context的同步集群重启信息到DBM
func syncClusterRestartedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationRestart)
}

// syncClusterHsWithCtx 带context的同步集群水平扩缩信息到DBM
func syncClusterHsWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationHscaling)
}

// syncClusterVsWithCtx 带context的同步集群垂直扩缩信息到DBM
func syncClusterVsWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationVscaling)
}

// syncClusterVeWithCtx 带 context 的同步集群磁盘扩缩信息到DBM
func syncClusterVeWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationVolumeExpand)
}

// syncClusterAbnormalWithCtx 带 context 的同步集群异常信息到DBM
func syncClusterAbnormalWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationStatusAbnormal)
}

// syncClusterNormalWithCtx 带 context 的同步集群正常信息到DBM
func syncClusterNormalWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationStatusNormal)
}

// syncClusterDeletedWithCtx 带context的同步集群删除信息到DBM
func syncClusterDeletedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationDelete)
}

// syncClusterCreatedWithCtx 带context的同步集群创建信息到DBM
func syncClusterCreatedWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	return syncClusterWithCtx(ctx, clusterEntity, dbmAPIService, coreconst.OperationCreate)
}

// syncClusterWithCtx 统一的带context的同步集群操作函数
func syncClusterWithCtx(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	operation coreconst.ClusterOperationType,
) error {
	// 检查 context 是否已取消
	if err := checkContextCancelled(ctx); err != nil {
		return err
	}

	dbmClusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType)
	if err != nil {
		return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
	}

	switch operation {
	case coreconst.OperationDelete:
		return syncClusterDelete(clusterEntity, dbmAPIService, dbmClusterType)
	case coreconst.OperationCreate:
		return syncClusterCreate(clusterEntity, dbmAPIService, dbmClusterType)
	case
		coreconst.OperationExpose,
		coreconst.OperationStop,
		coreconst.OperationStart,
		coreconst.OperationRestart,
		coreconst.OperationHscaling,
		coreconst.OperationVscaling,
		coreconst.OperationVolumeExpand,
		coreconst.OperationStatusNormal,
		coreconst.OperationStatusAbnormal:
		return syncClusterUpdate(clusterEntity, dbmAPIService, dbmClusterType, operation)
	default:
		return fmt.Errorf("不支持的同步操作类型: %s", operation)
	}
}

// getPhaseByOperation 根据操作类型获取对应的phase值
func getPhaseByOperation(operation coreconst.ClusterOperationType) coreconst.ClusterPhase {
	if operation == coreconst.OperationStatusAbnormal {
		return coreconst.PhaseOffline
	}
	return coreconst.PhaseOnline
}

// getStatusByOperation 根据操作类型获取对应的status值
func getStatusByOperation(operation coreconst.ClusterOperationType) coreconst.ClusterStatus {
	if operation == coreconst.OperationStatusAbnormal {
		return coreconst.StatusAbNormal
	}
	return coreconst.StatusNormal
}

// checkContextCancelled 检查context是否已取消
func checkContextCancelled(ctx context.Context) error {
	select {
	case <-ctx.Done():
		return fmt.Errorf("同步任务被取消: %w", ctx.Err())
	default:
		return nil
	}
}

// syncClusterDelete 同步集群删除操作
func syncClusterDelete(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	dbmClusterType string,
) error {
	syncRequest := buildDeleteRequest(clusterEntity, dbmClusterType)
	response, err := dbmAPIService.SyncClusterDeleted(syncRequest)
	return handleSyncResponse(err, response, "删除", clusterEntity.ClusterName)
}

// syncClusterCreate 同步集群创建操作
func syncClusterCreate(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	dbmClusterType string,
) error {
	syncRequest := buildCreateRequest(clusterEntity, dbmClusterType)
	response, err := dbmAPIService.SyncClusterCreated(syncRequest)
	return handleSyncResponse(err, response, "创建", clusterEntity.ClusterName)
}

// syncClusterUpdate 同步集群更新操作
func syncClusterUpdate(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	dbmClusterType string,
	operation coreconst.ClusterOperationType,
) error {
	phase := getPhaseByOperation(operation)
	status := getStatusByOperation(operation)
	syncRequest := buildUpdateRequest(clusterEntity, dbmClusterType, phase, status)
	response, err := dbmAPIService.SyncClusterUpdated(syncRequest)
	return handleSyncResponse(err, response, "更新", clusterEntity.ClusterName)
}

// buildDeleteRequest 构建删除请求
func buildDeleteRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmClusterType string,
) *infreq.DeleteClusterRequest {
	return &infreq.DeleteClusterRequest{
		Name:        clusterEntity.ClusterName,
		BkBizID:     clusterEntity.BkBizID,
		ClusterType: dbmClusterType,
	}
}

// buildCreateRequest 构建创建请求
func buildCreateRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmClusterType string,
) *infreq.CreateClusterRequest {
	return &infreq.CreateClusterRequest{
		Name:         clusterEntity.ClusterName,
		Alias:        clusterEntity.ClusterAlias,
		BkBizID:      clusterEntity.BkBizID,
		ClusterType:  dbmClusterType,
		ImmuteDomain: fmt.Sprintf("%d_%s_%s", clusterEntity.BkBizID, dbmClusterType, clusterEntity.ClusterName),
		MajorVersion: clusterEntity.ServiceVersion,
		Phase:        string(coreconst.PhaseOnline),
		Status:       string(coreconst.StatusNormal),
		Region:       "default",
		Operator:     clusterEntity.CreatedBy,
	}
}

// buildUpdateRequest 构建更新请求
func buildUpdateRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmClusterType string,
	phase coreconst.ClusterPhase,
	status coreconst.ClusterStatus,
) *infreq.UpdateClusterRequest {
	domain := clusterEntity.VIP
	if domain == "" {
		domain = fmt.Sprintf("%d_%s_%s", clusterEntity.BkBizID, dbmClusterType, clusterEntity.ClusterName)
	}
	return &infreq.UpdateClusterRequest{
		Name:             clusterEntity.ClusterName,
		Alias:            clusterEntity.ClusterAlias,
		BkBizID:          clusterEntity.BkBizID,
		ClusterType:      dbmClusterType,
		ImmuteDomain:     domain,
		MajorVersion:     clusterEntity.ServiceVersion,
		Phase:            string(phase),
		Status:           string(status),
		Region:           "default",
		Operator:         clusterEntity.UpdatedBy,
		ClusterEntryType: "clb",
	}
}

// handleSyncResponse 统一处理同步响应
func handleSyncResponse(err error, response infresp.DbmAPIResponse, operation string, clusterName string) error {
	if err != nil {
		return fmt.Errorf("调用%s同步接口失败: %w", operation, err)
	}
	if !response.Result {
		return fmt.Errorf("DBM API返回%s同步失败: %s", operation, response.Message)
	}
	slog.Info("DBM API 返回同步成功", "operation", operation, "cluster_name", clusterName)
	return nil
}
