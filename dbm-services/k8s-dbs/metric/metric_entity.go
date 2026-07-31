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

// 指标标签名称常量
const (
	MetricTagAPIName    = "api_name"
	MetricTagMethod     = "method"
	MetricTagStatus     = "status"
	MetricTagBkUserName = "bk_username"
	MetricTagBkAppCode  = "bk_app_code"
	MetricTagCode       = "code"
	MetricTagResult     = "result"
)

// BaseMetricTags 基础标签
type BaseMetricTags struct {
	APIName    string
	Method     string
	Status     string
	BkUserName string
	BkAppCode  string
	ResultCode string
	Result     string
}

// ClusterAPIMetricTags 集群 API 标签
type ClusterAPIMetricTags struct {
	K8sClusterName string
	Namespace      string
	ClusterName    string
	BaseMetricTags
}

// AddonAPIMetricTags Addon API 标签
type AddonAPIMetricTags struct {
	K8sClusterName string
	AddonType      string
	AddonVersion   string
	BaseMetricTags
}
