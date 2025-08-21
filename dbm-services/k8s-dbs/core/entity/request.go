/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License");
 * you may not use this file except in compliance with the License.
 *
 * You may obtain a copy of the License at
 * https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package entity

import (
	coreentity "k8s-dbs/common/entity"

	corev1 "k8s.io/api/core/v1"
)

// OpsRequestParams OpsRequest Params
type OpsRequestParams struct {
	Metadata      Metadata            `json:"metadata,omitempty"`
	ComponentList []ComponentResource `json:"componentList,omitempty"`
}

// Request Receive request structure
type Request struct {
	K8sClusterName    string   `json:"k8sClusterName,omitempty" required:"true"`
	BkBizID           uint64   `json:"bkBizId,omitempty"`
	BkBizName         string   `json:"bkBizName,omitempty"`
	BkAppAbbr         string   `json:"bkAppAbbr,omitempty"`
	Tags              []string `json:"tags,omitempty"`
	Metadata          `json:",inline"`
	Spec              `json:",inline"`
	coreentity.BKAuth `json:",inline"`
	Description       string `json:"description,omitempty"`
}

// OpsService 定义 OpsService 结构体
type OpsService struct {
	ComponentName string         `json:"componentName,omitempty"`
	Enable        bool           `json:"enable"`
	Service       ClusterService `json:"service,omitempty"`
}

// ClusterService 定义 ClusterService 结构体
type ClusterService struct {
	Name         string             `json:"name,omitempty"`
	ServiceType  corev1.ServiceType `json:"serviceType,omitempty"`
	Annotations  map[string]string  `json:"annotations,omitempty"`
	Ports        []int32            `json:"ports,omitempty"`
	RoleSelector string             `json:"roleSelector,omitempty"`
	PodSelect    map[string]string  `json:"podSelector,omitempty"`
	NodePorts    []int32            `json:"nodePorts,omitempty"`
	Protocols    []corev1.Protocol  `json:"protocols,omitempty"`
}
