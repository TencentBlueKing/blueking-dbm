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

// Package util 提供 infrastructure 模块的辅助工具函数
package util

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"regexp"
	"strings"
	"time"

	"github.com/pkg/errors"
	"golang.org/x/sync/errgroup"

	commconst "k8s-dbs/common/constant"
	coreconst "k8s-dbs/core/constant"
	infreq "k8s-dbs/infrastructure/request"
	infresp "k8s-dbs/infrastructure/response"
	"k8s-dbs/infrastructure/thirdapi"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
)

// domainSanitizeRegexp 匹配域名组成部分中不合法的字符（仅保留英文字母、数字、连字符）
var domainSanitizeRegexp = regexp.MustCompile("[^a-zA-Z0-9-]")

// ClusterEntryType 枚举 DBM 侧 ClusterEntry 表的 entry_type 取值。
type ClusterEntryType string

// 已知的 ClusterEntry 类型。
const (
	ClusterEntryTypeCLB ClusterEntryType = "clb"
)

// GetDbmClusterType 根据 addon 类型和拓扑名称获取 DBM cluster type。
func GetDbmClusterType(storageAddonType, topoName string) (string, error) {
	if clusterType, ok := commconst.ResolveClusterType(storageAddonType, topoName); ok {
		return clusterType, nil
	}
	return "", fmt.Errorf("不支持的存储插件类型: %s (topoName=%s)", storageAddonType, topoName)
}

// AsyncClusterCreated 同步集群创建信息到 DBM。
// onIDReceived 为可选回调，DBM 创建成功后将返回的 cluster id 通知调用方。
func AsyncClusterCreated(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	onIDReceived func(dbmClusterID uint64),
) {
	slog.Info("开始同步集群创建信息", "cluster_name", clusterEntity.ClusterName)
	syncFunc := func(ctx context.Context, entity *metaentity.K8sCrdClusterEntity, svc *thirdapi.DbmAPIService) error {
		if err := checkContextCancelled(ctx); err != nil {
			return err
		}
		dbmClusterType, err := GetDbmClusterType(entity.AddonInfo.AddonType, entity.TopoName)
		if err != nil {
			return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
		}
		syncRequest := BuildCreateRequest(entity, dbmClusterType)
		dbmClusterID, err := svc.SyncClusterCreated(syncRequest)
		if err != nil {
			return err
		}
		slog.Info("DBM API 返回同步成功", "operation", "创建",
			"cluster_name", entity.ClusterName, "dbm_cluster_id", dbmClusterID)
		if onIDReceived != nil {
			onIDReceived(dbmClusterID)
		}
		return nil
	}
	asyncClusterOperation(clusterEntity, coreconst.OperationCreate, dbmAPIService, syncFunc)
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

	dbmClusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	if err != nil {
		return fmt.Errorf("未找到对应的 dbm cluster type: %w", err)
	}

	switch operation {
	case coreconst.OperationDelete:
		return syncClusterDelete(clusterEntity, dbmAPIService, dbmClusterType)
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

// syncClusterUpdate 同步集群更新操作
func syncClusterUpdate(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	dbmClusterType string,
	operation coreconst.ClusterOperationType,
) error {
	phase := getPhaseByOperation(operation)
	status := getStatusByOperation(operation)
	// 目前仅支持 CLB
	syncRequest := buildUpdateRequest(clusterEntity, dbmClusterType, phase, status, ClusterEntryTypeCLB)
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

// BuildCreateRequest 构建创建请求
func BuildCreateRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmClusterType string,
) *infreq.CreateClusterRequest {
	alias := clusterEntity.ClusterAlias
	if alias == "" {
		alias = clusterEntity.ClusterName
	}
	return &infreq.CreateClusterRequest{
		Name:         clusterEntity.ClusterName,
		Alias:        alias,
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
	entryType ClusterEntryType,
) *infreq.UpdateClusterRequest {
	domain := clusterEntity.VIP
	if domain == "" {
		domain = fmt.Sprintf("%d_%s_%s", clusterEntity.BkBizID, dbmClusterType, clusterEntity.ClusterName)
	}
	alias := clusterEntity.ClusterAlias
	if alias == "" {
		alias = clusterEntity.ClusterName
	}
	return &infreq.UpdateClusterRequest{
		Name:             clusterEntity.ClusterName,
		Alias:            alias,
		BkBizID:          clusterEntity.BkBizID,
		ClusterType:      dbmClusterType,
		ImmuteDomain:     domain,
		MajorVersion:     clusterEntity.ServiceVersion,
		Phase:            string(phase),
		Status:           string(status),
		Region:           "default",
		Operator:         clusterEntity.UpdatedBy,
		ClusterEntryType: string(entryType),
	}
}

// SanitizeForDomain 清理字符串使其适用于域名组成部分。
func SanitizeForDomain(s string) string {
	s = strings.ReplaceAll(s, "_", "-")
	s = domainSanitizeRegexp.ReplaceAllString(s, "")
	s = strings.ToLower(s)
	return s
}

// BuildDomainName 根据集群信息组装自定义域名。
func BuildDomainName(clusterType, clusterName, bkAppAbbr string) string {
	clusterType = SanitizeForDomain(clusterType)
	clusterName = SanitizeForDomain(clusterName)
	bkAppAbbr = SanitizeForDomain(bkAppAbbr)
	return strings.Join([]string{clusterType, clusterName, bkAppAbbr, "db"}, ".")
}

// BuildDomainInstances 根据外部地址构建 instances 列表。
// 同一个 K8s LoadBalancer Service 的多个端口共用同一 VIP（均来自
// status.loadBalancer.ingress[0]），因此只需取第一个可解析地址的 IP
// 生成一条 instance 记录即可。
func BuildDomainInstances(externalAddrs string) []string {
	for _, addr := range strings.Split(externalAddrs, ",") {
		addr = strings.TrimSpace(addr)
		if addr == "" {
			continue
		}
		host, _, err := net.SplitHostPort(addr)
		if err != nil {
			slog.Warn("BuildDomainInstances: skip invalid addr", "addr", addr, "error", err)
			continue
		}
		if host == "" {
			continue
		}
		return []string{fmt.Sprintf("%s#%s", host, "0")}
	}
	slog.Warn("BuildDomainInstances: no valid addr found", "externalAddrs", externalAddrs)
	return []string{}
}

// BuildCreateDomainRequest 组装完整的域名创建请求。
func BuildCreateDomainRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	serviceEntity *metaentity.K8sClusterServiceEntity,
) (*infreq.CreateDomainRequest, error) {
	clusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	if err != nil {
		return nil, fmt.Errorf("GetDbmClusterType failed: %w", err)
	}
	domain := BuildDomainName(clusterType, clusterEntity.ClusterName, clusterEntity.BkAppAbbr)
	instances := BuildDomainInstances(serviceEntity.ExternalAddrs)
	if len(instances) == 0 {
		return nil, fmt.Errorf("BuildDomainInstances failed: instances is empty")
	}
	return &infreq.CreateDomainRequest{
		BkCloudID:   0,
		BkBizID:     clusterEntity.BkBizID,
		ClusterType: clusterType,
		Name:        clusterEntity.ClusterName,
		Domain:      domain,
		Instances:   instances,
		Role:        "master_entry",
		Operator:    clusterEntity.CreatedBy,
	}, nil
}

// BuildGetDomainRequest 组装域名查询请求。
func BuildGetDomainRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	domain string,
) (*infreq.GetDomainRequest, error) {
	clusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	if err != nil {
		return nil, fmt.Errorf("GetDbmClusterType failed: %w", err)
	}
	return &infreq.GetDomainRequest{
		BkCloudID:   0,
		BkBizID:     clusterEntity.BkBizID,
		ClusterType: clusterType,
		Name:        clusterEntity.ClusterName,
		Domain:      domain,
	}, nil
}

// BuildDeleteDomainRequest 组装域名删除请求。
func BuildDeleteDomainRequest(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	domain string,
) (*infreq.DeleteDomainRequest, error) {
	clusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	if err != nil {
		return nil, fmt.Errorf("GetDbmClusterType failed: %w", err)
	}
	return &infreq.DeleteDomainRequest{
		BkCloudID:   0,
		BkBizID:     clusterEntity.BkBizID,
		ClusterType: clusterType,
		Name:        clusterEntity.ClusterName,
		Domain:      domain,
		Operator:    clusterEntity.CreatedBy,
	}, nil
}

// BuildDomainNameFromCluster 根据集群信息构建域名字符串，供无 serviceEntity 的场景使用。
func BuildDomainNameFromCluster(clusterEntity *metaentity.K8sCrdClusterEntity) (string, error) {
	clusterType, err := GetDbmClusterType(clusterEntity.AddonInfo.AddonType, clusterEntity.TopoName)
	if err != nil {
		return "", fmt.Errorf("GetDbmClusterType failed: %w", err)
	}
	return BuildDomainName(clusterType, clusterEntity.ClusterName, clusterEntity.BkAppAbbr), nil
}

// AsyncDomainCreate 异步创建域名（集群首次暴露时调用）。
// DBM 侧域名创建成功后，会把生成的域名回写到本地 tb_k8s_cluster_service.domains 字段。
func AsyncDomainCreate(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	serviceEntity *metaentity.K8sClusterServiceEntity,
	dbmAPIService *thirdapi.DbmAPIService,
	serviceProvider metaprovider.K8sClusterServiceProvider,
) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)

	g := &errgroup.Group{}

	var createReq *infreq.CreateDomainRequest

	g.Go(func() error {
		if err := checkContextCancelled(ctx); err != nil {
			return err
		}

		req, err := BuildCreateDomainRequest(clusterEntity, serviceEntity)
		if err != nil {
			return fmt.Errorf("BuildCreateDomainRequest failed: %w", err)
		}

		if _, createErr := dbmAPIService.SyncDomainCreated(req); createErr != nil {
			return fmt.Errorf("SyncDomainCreated failed: %w", createErr)
		}
		createReq = req
		return nil
	})

	go func() {
		defer cancel()
		if err := g.Wait(); err != nil {
			if errors.Is(err, context.DeadlineExceeded) {
				slog.Warn("DBM API 创建域名超时",
					"cluster_name", clusterEntity.ClusterName)
			} else {
				slog.Error("DBM API 创建域名失败",
					"cluster_name", clusterEntity.ClusterName,
					"error", err)
			}
			return
		}

		// g.Wait() 返回后，createReq 的写入对此处可见（errgroup 保证 happens-before）
		if createReq == nil || createReq.Domain == "" {
			return
		}

		slog.Info("DBM API 创建域名成功",
			"cluster_name", clusterEntity.ClusterName,
			"domain", createReq.Domain)

		// DBM 创建成功后，将域名回写到本地 service 记录
		if serviceProvider == nil {
			return
		}
		if _, upErr := serviceProvider.UpdateDomains(
			serviceEntity.CrdClusterID,
			serviceEntity.ServiceName,
			createReq.Domain,
		); upErr != nil {
			slog.Error("回写 service.domains 字段失败",
				"cluster_name", clusterEntity.ClusterName,
				"service_name", serviceEntity.ServiceName,
				"domain", createReq.Domain,
				"error", upErr)
		}
	}()
}

// AsyncDomainDelete 异步删除域名（集群完全取消暴露或集群删除时调用）。
func AsyncDomainDelete(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)

	g := &errgroup.Group{}

	g.Go(func() error {
		if err := checkContextCancelled(ctx); err != nil {
			return err
		}

		domain, err := BuildDomainNameFromCluster(clusterEntity)
		if err != nil {
			return fmt.Errorf("BuildDomainNameFromCluster failed: %w", err)
		}

		delReq, err := BuildDeleteDomainRequest(clusterEntity, domain)
		if err != nil {
			return fmt.Errorf("BuildDeleteDomainRequest failed: %w", err)
		}

		if _, delErr := dbmAPIService.SyncDomainDeleted(delReq); delErr != nil {
			return fmt.Errorf("SyncDomainDeleted failed: %w", delErr)
		}

		return nil
	})

	go func() {
		defer cancel()
		if err := g.Wait(); err != nil {
			if errors.Is(err, context.DeadlineExceeded) {
				slog.Warn("DBM API 删除域名超时",
					"cluster_name", clusterEntity.ClusterName)
			} else {
				slog.Error("DBM API 删除域名失败",
					"cluster_name", clusterEntity.ClusterName,
					"error", err)
			}
		} else {
			slog.Info("DBM API 删除域名成功",
				"cluster_name", clusterEntity.ClusterName)
		}
	}()
}

// runDomainDelete 阻塞执行一次 DBM 删除域名请求。
// 复用 AsyncDomainDelete 的参数构建与错误语义，便于上层做串行化组合。
func runDomainDelete(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := checkContextCancelled(ctx); err != nil {
		return err
	}
	domain, err := BuildDomainNameFromCluster(clusterEntity)
	if err != nil {
		return fmt.Errorf("BuildDomainNameFromCluster failed: %w", err)
	}
	delReq, err := BuildDeleteDomainRequest(clusterEntity, domain)
	if err != nil {
		return fmt.Errorf("BuildDeleteDomainRequest failed: %w", err)
	}
	if _, delErr := dbmAPIService.SyncDomainDeleted(delReq); delErr != nil {
		return fmt.Errorf("SyncDomainDeleted failed: %w", delErr)
	}
	return nil
}

// runClusterDelete 阻塞执行一次 DBM 删除集群元数据请求。
func runClusterDelete(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) error {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	return syncClusterDeletedWithCtx(ctx, clusterEntity, dbmAPIService)
}

// AsyncClusterTeardown 下架集群时对 DBM 的组合同步：先删域名、再删 Cluster 元数据。
//
// 本函数自身立即返回，内部 goroutine 串行执行，避免并发下的竞态；
func AsyncClusterTeardown(
	clusterEntity *metaentity.K8sCrdClusterEntity,
	dbmAPIService *thirdapi.DbmAPIService,
) {
	go func() {
		// 1) 先删 DBM 域名（此时 Cluster 仍存在，DBM 校验能通过）
		if err := runDomainDelete(clusterEntity, dbmAPIService); err != nil {
			slog.Error("下架集群: DBM 删除域名失败",
				"cluster_name", clusterEntity.ClusterName,
				"namespace", clusterEntity.Namespace,
				"error", err)
		} else {
			slog.Info("下架集群: DBM 删除域名成功",
				"cluster_name", clusterEntity.ClusterName)
		}

		// 2) 再删 DBM Cluster 元数据（此接口会级联清掉剩余 ClusterEntry）
		if err := runClusterDelete(clusterEntity, dbmAPIService); err != nil {
			slog.Error("下架集群: DBM 删除集群元数据失败",
				"cluster_name", clusterEntity.ClusterName,
				"namespace", clusterEntity.Namespace,
				"error", err)
		} else {
			slog.Info("下架集群: DBM 删除集群元数据成功",
				"cluster_name", clusterEntity.ClusterName)
		}
	}()
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
