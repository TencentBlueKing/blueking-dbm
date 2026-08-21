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

package middleware

import (
	"errors"
	"fmt"
	"log/slog"
	"sync"

	"github.com/tidwall/gjson"

	"k8s-dbs/common/constant"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
)

// resolverError 标记由 resolver 产生的本地错误（DB 不可达、参数缺失、类型不匹配等），
// 区别于 IAM 远程调用错误，方便中间件返回不同的错误码。
type resolverError struct {
	err error
}

func (e *resolverError) Error() string { return e.err.Error() }
func (e *resolverError) Unwrap() error { return e.err }

func newResolverError(format string, args ...interface{}) error {
	return &resolverError{err: fmt.Errorf(format, args...)}
}

// IsResolverError 判断是否为 resolver 本地解析错误。
func IsResolverError(err error) bool {
	var re *resolverError
	return errors.As(err, &re)
}

// ResolveResult 包含 resolver 推断出的集群类型和可选的 DBM cluster ID。
type ResolveResult struct {
	ClusterType  string // cluster_type，如 "k8s_surrealdb_ha"
	AddonType    string // addon_type，如 "surrealdb"，用于存储白名单匹配
	DbmClusterID uint64 // DBM 侧的集群 ID（非创建操作从本地 DB 获取，创建操作为 0）
	BkBizID      uint64 // 业务 ID（非创建操作从本地 DB 获取，创建操作为 0）
}

// ClusterTypeResolver 从请求上下文中推断 IAM cluster_type。
// 创建操作从请求体提取 storageAddonType；非创建操作从 DB 查询。
type ClusterTypeResolver interface {
	Resolve(apiName string, rawJSON []byte) (*ResolveResult, error)
}

// DBClusterTypeResolver 通过数据库查询推断集群类型。
// 首次请求到达时通过 sync.Once 获取已初始化的单例。
type DBClusterTypeResolver struct {
	configProvider  metaprovider.K8sClusterConfigProvider
	clusterProvider metaprovider.K8sCrdClusterProvider
	once            sync.Once
	initErr         error
}

// NewDBClusterTypeResolver 创建 DBClusterTypeResolver（无参构造，懒加载 provider）
func NewDBClusterTypeResolver() *DBClusterTypeResolver {
	return &DBClusterTypeResolver{}
}

// initProviders 懒加载获取已初始化的 provider 单例。
func (r *DBClusterTypeResolver) initProviders() error {
	r.once.Do(func() {
		defer func() {
			if rec := recover(); rec != nil {
				r.initErr = fmt.Errorf("provider 尚未初始化: %v", rec)
			}
		}()
		// 不传参数 — 获取已由 BuildRouter 初始化的单例
		r.configProvider = metaprovider.GetK8sClusterConfigProvider(nil)
		r.clusterProvider = metaprovider.GetK8sCrdClusterProvider()
	})
	return r.initErr
}

// Resolve 根据 apiName 和原始请求体推断 cluster_type。
//
// 创建操作：从请求体提取 storageAddonType + topoName → ResolveClusterType。
// 非创建操作：DB 查询 → addonType + topoName → ResolveClusterType + DbmClusterID。
func (r *DBClusterTypeResolver) Resolve(apiName string, rawJSON []byte) (*ResolveResult, error) {
	if apiName == constant.APIClusterCreate {
		return r.resolveForCreate(rawJSON)
	}
	return r.resolveForNonCreate(apiName, rawJSON)
}

// resolveForCreate 从请求体提取 storageAddonType + topoName 并解析出 cluster_type。
// 兼容 Core API（顶层字段）和 Dataweb API（basicInfo / resourceConfig 嵌套字段）。
func (r *DBClusterTypeResolver) resolveForCreate(rawJSON []byte) (*ResolveResult, error) {
	addonType := gjsonFirstString(rawJSON, "storageAddonType", "basicInfo.storageAddonType")
	if addonType == "" {
		return nil, newResolverError("创建操作缺少 storageAddonType 字段")
	}
	topoName := gjsonFirstString(rawJSON, "topoName", "resourceConfig.topoName")

	clusterType, ok := constant.ResolveClusterType(addonType, topoName)
	if !ok {
		return nil, newResolverError("未知的 addon 类型: %s (topoName=%s)", addonType, topoName)
	}
	return &ResolveResult{ClusterType: clusterType, AddonType: addonType, DbmClusterID: 0}, nil
}

// resolveForNonCreate 从 DB 查询集群的 addonType 并映射到 IAM cluster_type。
// 同时返回集群的 DbmClusterID，供鉴权中间件作为 resource_id 传给 DBM。
// 如果请求体显式包含 cluster_type，会与 DB 结果校验一致性。
func (r *DBClusterTypeResolver) resolveForNonCreate(apiName string, rawJSON []byte) (*ResolveResult, error) {
	if err := r.initProviders(); err != nil {
		return nil, newResolverError("集群类型解析器初始化失败: %v", err)
	}

	k8sClusterName := gjsonFirstString(rawJSON, "k8sClusterName", "deploymentEnv.k8sClusterName")
	namespace := gjsonFirstString(rawJSON, "namespace", "basicInfo.namespace")
	clusterName := gjsonFirstString(rawJSON, "clusterName", "basicInfo.clusterName")

	if k8sClusterName == "" || namespace == "" || clusterName == "" {
		return nil, newResolverError(
			"非创建操作缺少必要字段: k8sClusterName=%q, namespace=%q, clusterName=%q",
			k8sClusterName, namespace, clusterName)
	}

	// Step 1: k8sClusterName → configEntity.ID
	configEntity, err := r.configProvider.FindConfigByName(k8sClusterName)
	if err != nil {
		return nil, newResolverError("查询 K8s 集群配置失败 (k8sClusterName=%s): %v", k8sClusterName, err)
	}
	if configEntity == nil {
		return nil, newResolverError("K8s 集群配置不存在: %s", k8sClusterName)
	}

	// Step 2: configID + namespace + clusterName → clusterEntity
	queryParams := &metaentity.ClusterQueryParams{
		K8sClusterConfigID: configEntity.ID,
		Namespace:          namespace,
		ClusterName:        clusterName,
	}
	clusterEntity, err := r.clusterProvider.FindByParams(queryParams)
	if err != nil {
		return nil, newResolverError("查询集群失败 (config=%d, ns=%s, cluster=%s): %v",
			configEntity.ID, namespace, clusterName, err)
	}
	if clusterEntity == nil {
		return nil, newResolverError("集群不存在: config=%d, ns=%s, cluster=%s",
			configEntity.ID, namespace, clusterName)
	}

	// Step 3: addonType + topoName → cluster_type
	if clusterEntity.AddonInfo == nil {
		return nil, newResolverError("集群 AddonInfo 为空: cluster=%s", clusterName)
	}
	addonType := clusterEntity.AddonInfo.AddonType
	clusterType, ok := constant.ResolveClusterType(addonType, clusterEntity.TopoName)
	if !ok {
		return nil, newResolverError("未知的 addon 类型: %s (topoName=%s, cluster=%s)",
			addonType, clusterEntity.TopoName, clusterName)
	}

	// 安全性校验：如果请求体显式包含 cluster_type，与 DB 结果比较
	if explicitCT := gjson.GetBytes(rawJSON, "cluster_type").String(); explicitCT != "" {
		if explicitCT != clusterType {
			slog.Warn("请求体 cluster_type 与数据库不一致，拒绝请求",
				"explicit", explicitCT, "fromDB", clusterType,
				"cluster", clusterName, "api", apiName)
			return nil, newResolverError(
				"请求体 cluster_type (%s) 与数据库记录 (%s) 不一致", explicitCT, clusterType)
		}
		slog.Debug("请求体 cluster_type 与数据库一致", "clusterType", clusterType)
	}

	return &ResolveResult{
		ClusterType:  clusterType,
		AddonType:    addonType,
		DbmClusterID: clusterEntity.DbmClusterID,
		BkBizID:      clusterEntity.BkBizID,
	}, nil
}

// gjsonFirstString 按优先级从 rawJSON 中提取第一个非空字符串值。
// 利用 gjson 的 dot 路径语法天然支持嵌套查询（如 "basicInfo.storageAddonType"）。
func gjsonFirstString(rawJSON []byte, paths ...string) string {
	for _, path := range paths {
		if val := gjson.GetBytes(rawJSON, path).String(); val != "" {
			return val
		}
	}
	return ""
}

// gjsonFirstInt 按优先级从 rawJSON 中提取第一个正整数值。
func gjsonFirstInt(rawJSON []byte, paths ...string) int64 {
	for _, path := range paths {
		if r := gjson.GetBytes(rawJSON, path); r.Exists() && r.Int() > 0 {
			return r.Int()
		}
	}
	return 0
}
