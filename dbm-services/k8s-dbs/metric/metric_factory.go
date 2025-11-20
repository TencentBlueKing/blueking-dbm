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

package metric

import "fmt"

// ClusterMetricFetcher 集群指标接口
type ClusterMetricFetcher interface {
	// GetStorageUsage 获取存储使用量，单位：GB
	GetStorageUsage(params *ClusterMetricQueryParams) (float64, error)
}

var FetcherFactory = &ClusterMetricFetcherFactory{}

// ClusterMetricFetcherFactory 集群指标 Factory
type ClusterMetricFetcherFactory struct{}

func (c *ClusterMetricFetcherFactory) getClusterMetricFetcher(addonType string) (ClusterMetricFetcher, error) {
	switch addonType {
	case "victoriametrics":
		return &VMClusterMetricFetcher{}, nil
	case "surrealdb":
		return nil, fmt.Errorf("not supported yet")
	case "milvus":
		return nil, fmt.Errorf("not supported yet")
	case "qdrant":
		return nil, fmt.Errorf("not supported yet")
	case "minio":
		return nil, fmt.Errorf("not supported yet")
	default:
		return nil, fmt.Errorf("not supported addon type: %s", addonType)
	}
}

// GetStorageUsage 获取存储使用量
func (c *ClusterMetricFetcherFactory) GetStorageUsage(params *ClusterMetricQueryParams) (float64, error) {
	fetcher, err := c.getClusterMetricFetcher(params.AddonType)
	if err != nil {
		return 0, err
	}
	return fetcher.GetStorageUsage(params)
}

// ClusterMetricQueryParams 集群指标查询参数
type ClusterMetricQueryParams struct {
	AddonType      string `json:"addonType"`
	K8sClusterName string `json:"k8sClusterName"`
	Namespace      string `json:"namespace"`
	PodName        string `json:"podName"`
	JobName        string `json:"jobName"`
}
