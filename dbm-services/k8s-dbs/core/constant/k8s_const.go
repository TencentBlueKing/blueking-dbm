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

package constant

import "time"

// k8s service 类型
const (
	LoadBalancer = "LoadBalancer"
	ClusterIP    = "ClusterIP"
	NodePort     = "NodePort"
)

// K8sAPIServerTimeout k8s API server 默认超时时间
const K8sAPIServerTimeout = 60 * time.Second

const (
	// MaxPodLogLines pod log 返回最大行数
	MaxPodLogLines = 2000
	// MaxPodLogSize pod log 返回最大字节数
	MaxPodLogSize = 5 * 1024 * 1024
	// PodLogBufferSize pod log scanner 初始缓冲区字节数
	PodLogBufferSize = 64 * 1024
	// MaxPodLogLineBytes pod log 单行最大字节数
	MaxPodLogLineBytes = 2 * 1024 * 1024
)
