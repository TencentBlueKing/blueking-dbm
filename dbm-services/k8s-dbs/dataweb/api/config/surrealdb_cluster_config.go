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

package config

import (
	coreentity "k8s-dbs/core/entity"
	webreq "k8s-dbs/dataweb/vo/request"
)

// surrealdbSensitiveEnvKeys surrealdb 需屏蔽的 env 字段
var surrealdbSensitiveEnvKeys = []string{"SURREAL_PATH"}

// SurrealDBClusterConfigBuilder surrealdb 集群配置构建器
type SurrealDBClusterConfigBuilder struct {
	BaseClusterConfigBuilder
}

// BuildEnvConfig 构建surrealdb env，屏蔽敏感字段
func (b *SurrealDBClusterConfigBuilder) BuildEnvConfig(
	request *webreq.ClusterUpdatedRequest,
) (*coreentity.Request, error) {
	filterSensitiveConfig(request, surrealdbSensitiveEnvKeys)
	return b.BaseClusterConfigBuilder.BuildEnvConfig(request)
}

// ParseEnvConfig 解析Env，屏蔽敏感字段
func (b *SurrealDBClusterConfigBuilder) ParseEnvConfig(
	request *coreentity.ComponentDetail,
) (*webreq.ComponentDetail, error) {
	result, err := b.BaseClusterConfigBuilder.ParseEnvConfig(request)
	if err != nil {
		return nil, err
	}
	for _, key := range surrealdbSensitiveEnvKeys {
		delete(result.Config, key)
	}
	return result, nil
}

// filterSensitiveConfig 从请求的 component config 中删除敏感字段
func filterSensitiveConfig(request *webreq.ClusterUpdatedRequest, sensitiveKeys []string) {
	for i := range request.ComponentList {
		config := request.ComponentList[i].Config
		if config == nil {
			continue
		}
		for _, key := range sensitiveKeys {
			delete(config, key)
		}
	}
}
