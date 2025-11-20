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

import (
	commconst "k8s-dbs/common/constant"
	coreentity "k8s-dbs/core/entity"
	"log/slog"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// ClusterAPITotalMetric cluster api 计数统计指标
const ClusterAPITotalMetric = "k8s_dbs_cluster_api_total"

var ClusterAPITotalMetricTags = []string{
	"api_name",
	"method",
	"k8s_cluster_name",
	"namespace",
	"cluster_name",
	"bk_username",
	"bk_app_code",
	"status",
	"code",
	"result",
}

// ClusterAPITotalCounter Cluster API 请求总数
var ClusterAPITotalCounter = promauto.NewCounterVec(
	prometheus.CounterOpts{
		Name: ClusterAPITotalMetric,
		Help: "Total number of cluster api by api_name, result and status code",
	},
	ClusterAPITotalMetricTags,
)

// ReportClusterAPIMetrics cluster api 指标上报
func ReportClusterAPIMetrics(c *gin.Context, basicMetricTags BaseMetricTags) {
	// 获取 APIGroup
	apiGroup := commconst.GetAPIGroup(c.GetString(commconst.APIName))
	if apiGroup != commconst.APIGroupCluster {
		return
	}

	requestEntity, ok := c.Get(commconst.APIRequestEntity)
	if !ok {
		slog.Warn("无法获取 cluster api 操作请求参数")
		return
	}

	clusterRequest, ok := requestEntity.(*coreentity.Request)
	if !ok {
		slog.Warn("请求实体类型断言失败")
		return
	}

	clusterMetricTags := ClusterAPIMetricTags{
		K8sClusterName: clusterRequest.K8sClusterName,
		Namespace:      clusterRequest.Namespace,
		ClusterName:    clusterRequest.ClusterName,
		BaseMetricTags: basicMetricTags,
	}

	ClusterAPITotalCounter.WithLabelValues(
		clusterMetricTags.APIName,
		clusterMetricTags.Method,
		clusterMetricTags.K8sClusterName,
		clusterMetricTags.Namespace,
		clusterMetricTags.ClusterName,
		clusterMetricTags.BkUserName,
		clusterMetricTags.BkAppCode,
		clusterMetricTags.Status,
		clusterMetricTags.ResultCode,
		clusterMetricTags.Result,
	).Inc()
}
