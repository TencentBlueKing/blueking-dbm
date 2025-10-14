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
