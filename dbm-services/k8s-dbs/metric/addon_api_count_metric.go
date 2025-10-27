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
	corereq "k8s-dbs/core/vo/request"
	"log/slog"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// AddonAPITotalMetric Addon api 计数统计指标
const AddonAPITotalMetric = "k8s_dbs_addon_api_total"

var AddonAPITotalMetricTags = []string{
	"api_name",
	"method",
	"k8s_cluster_name",
	"addon_type",
	"addon_version",
	"bk_username",
	"bk_app_code",
	"status",
	"code",
	"result",
}

// AddonAPITotalCounter Addon API 请求总数
var AddonAPITotalCounter = promauto.NewCounterVec(
	prometheus.CounterOpts{
		Name: AddonAPITotalMetric,
		Help: "Total number of addon api by api_name, result and status code",
	},
	AddonAPITotalMetricTags,
)

// ReportAddonAPIMetrics addon api 指标上报
func ReportAddonAPIMetrics(c *gin.Context, basicMetricTags BaseMetricTags) {
	// 获取 APIGroup
	apiGroup := commconst.GetAPIGroup(c.GetString(commconst.APIName))
	if apiGroup != commconst.APIGroupAddon {
		return
	}

	requestEntity, ok := c.Get(commconst.APIRequestEntity)
	if !ok {
		slog.Warn("无法获取 addon api 操作请求参数")
		return
	}

	addonOpRequest, ok := requestEntity.(*corereq.AddonOperationRequest)
	if !ok {
		slog.Warn("请求实体类型断言失败")
		return
	}

	addonMetricTags := AddonAPIMetricTags{
		K8sClusterName: addonOpRequest.K8sClusterName,
		AddonType:      addonOpRequest.AddonType,
		AddonVersion:   addonOpRequest.AddonVersion,
		BaseMetricTags: basicMetricTags,
	}

	AddonAPITotalCounter.WithLabelValues(
		addonMetricTags.APIName,
		addonMetricTags.Method,
		addonMetricTags.K8sClusterName,
		addonMetricTags.AddonType,
		addonMetricTags.AddonVersion,
		addonMetricTags.BkUserName,
		addonMetricTags.BkAppCode,
		addonMetricTags.Status,
		addonMetricTags.ResultCode,
		addonMetricTags.Result,
	).Inc()
}
