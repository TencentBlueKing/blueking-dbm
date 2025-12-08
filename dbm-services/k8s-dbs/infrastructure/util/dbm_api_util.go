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

// AsyncClusterOperation 通用的异步集群操作函数，支持创建、更新和删除操作
func AsyncClusterOperation(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	operationType string,
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
				slog.Warn("同步集群"+operationType+"信息超时",
					"cluster_name", clusterEntity.ClusterName,
					"namespace", clusterEntity.Namespace,
					"timeout", "30s",
				)
			} else {
				slog.Error("同步集群"+operationType+"信息失败",
					"cluster_name", clusterEntity.ClusterName,
					"namespace", clusterEntity.Namespace,
					"error", err,
				)
			}
		} else {
			slog.Info("同步集群"+operationType+"信息成功",
				"cluster_name", clusterEntity.ClusterName,
				"namespace", clusterEntity.Namespace,
			)
		}
	}()
}

// AsyncClusterCreated 同步集群创建信息到DBM
func AsyncClusterCreated(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群创建信息", "cluster_name", clusterEntity.ClusterName)
	AsyncClusterOperation(clusterEntity, "create", dbmAPIService, syncClusterCreatedWithContext)
}

// AsyncClusterDeleted 同步集群删除信息到DBM
func AsyncClusterDeleted(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群删除信息", "cluster_name", clusterEntity.ClusterName)
	AsyncClusterOperation(clusterEntity, "delete", dbmAPIService, syncClusterDeletedWithContext)
}

// AsyncClusterExposed 同步集群服务暴露信息到DBM
func AsyncClusterExposed(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	slog.Info("开始同步集群暴露信息", "cluster_name", clusterEntity.ClusterName)
	AsyncClusterOperation(clusterEntity, "expose", dbmAPIService, syncClusterExposedWithContext)
}

// syncClusterDeletedWithContext 带context的同步集群删除信息到DBM
func syncClusterDeletedWithContext(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	// 检查context是否已取消
	select {
	case <-ctx.Done():
		return fmt.Errorf("同步任务被取消: %w", ctx.Err())
	default:
	}

	dbmClusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType)
	if err != nil {
		return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
	}

	// 构建同步请求
	syncRequest := &infreq.DeleteClusterRequest{
		Name:        clusterEntity.ClusterName,
		BkBizID:     clusterEntity.BkBizID,
		ClusterType: dbmClusterType,
	}

	// 调用同步接口，支持context取消
	response, err := dbmAPIService.SyncClusterDeleted(syncRequest)
	if err != nil {
		return fmt.Errorf("调用同步接口失败: %w", err)
	}

	if !response.Result {
		return fmt.Errorf("DBM API返回同步失败: %s", response.Message)
	}
	slog.Info("DBM API 返回同步删除成功", "cluster_name", clusterEntity.ClusterName)
	return nil
}

// syncClusterCreatedWithContext 带context的同步集群创建信息到DBM
func syncClusterCreatedWithContext(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	// 检查context是否已取消
	select {
	case <-ctx.Done():
		return fmt.Errorf("同步任务被取消: %w", ctx.Err())
	default:
	}

	dbmClusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType)
	if err != nil {
		return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
	}

	// 构建同步请求
	syncRequest := &infreq.CreateClusterRequest{
		Name:         clusterEntity.ClusterName,
		Alias:        clusterEntity.ClusterAlias,
		BkBizID:      clusterEntity.BkBizID,
		ClusterType:  dbmClusterType,
		ImmuteDomain: fmt.Sprintf("%d_%s_%s", clusterEntity.BkBizID, dbmClusterType, clusterEntity.ClusterName),
		MajorVersion: clusterEntity.ServiceVersion,
		Phase:        "online",
		Status:       "normal",
		Region:       "default",
		Operator:     clusterEntity.CreatedBy,
	}

	// 调用同步接口，支持context取消
	response, err := dbmAPIService.SyncClusterCreated(syncRequest)
	if err != nil {
		return fmt.Errorf("调用同步接口失败: %w", err)
	}

	if !response.Result {
		return fmt.Errorf("DBM API返回同步失败: %s", response.Message)
	}
	slog.Info("DBM API 返回同步创建成功", "cluster_name", clusterEntity.ClusterName)
	return nil
}

// syncClusterExposedWithContext 带context的同步集群暴露信息到DBM
func syncClusterExposedWithContext(
	ctx context.Context,
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	// 检查context是否已取消
	select {
	case <-ctx.Done():
		return fmt.Errorf("同步任务被取消: %w", ctx.Err())
	default:
	}

	dbmClusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType)
	if err != nil {
		return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
	}

	// 构建同步请求
	syncRequest := &infreq.UpdateClusterRequest{
		Name:             clusterEntity.ClusterName,
		Alias:            clusterEntity.ClusterAlias,
		BkBizID:          clusterEntity.BkBizID,
		ClusterType:      dbmClusterType,
		ImmuteDomain:     clusterEntity.VIP,
		MajorVersion:     clusterEntity.ServiceVersion,
		Phase:            "online",
		Status:           "normal",
		Region:           "default",
		Operator:         clusterEntity.UpdatedBy,
		ClusterEntryType: "clb",
	}

	// 调用同步接口，支持context取消
	response, err := dbmAPIService.SyncClusterUpdated(syncRequest)
	if err != nil {
		return fmt.Errorf("调用同步接口失败: %w", err)
	}

	if !response.Result {
		return fmt.Errorf("DBM API返回同步失败: %s", response.Message)
	}
	slog.Info("DBM API 返回同步更新成功", "cluster_name", clusterEntity.ClusterName)
	return nil
}
