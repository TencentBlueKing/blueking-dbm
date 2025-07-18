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

package response

import (
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClusterStatusResponse cluster status response
type ClusterStatusResponse struct {
	Phase      kbv1.ClusterPhase `json:"phase,omitempty"`
	CreateTime metav1.Time       `json:"createTime,omitempty"`
	UpdateTime metav1.Time       `json:"updateTime,omitempty"`
}
