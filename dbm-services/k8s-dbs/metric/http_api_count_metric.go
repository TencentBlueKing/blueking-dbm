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

// HTTPAPITotalMetric api 计数统计指标
const HTTPAPITotalMetric = "k8s_dbs_http_api_total"

var HTTPAPITotalMetricTags = []string{
	"api_name",
	"method",
	"status",
	"bk_username",
	"bk_app_code",
	"code",
	"result",
}

// HTTPAPITotalCounter HTTP 请求总数
var HTTPAPITotalCounter = promauto.NewCounterVec(
	prometheus.CounterOpts{
		Name: HTTPAPITotalMetric,
		Help: "Total number of HTTP requests by method, path and status code.",
	},
	HTTPAPITotalMetricTags,
)
