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

package entity

import (
	commentity "k8s-dbs/common/entity"
)

// VMExposeInstanceRequest vmstorage 实例级 CLB 启停请求
type VMExposeInstanceRequest struct {
	DbmClusterID            uint64 `json:"dbmClusterId" binding:"required" msg:"dbmClusterId 字段不能为空"`
	K8sClusterName          string `json:"k8sClusterName" binding:"required" msg:"k8sClusterName 字段不能为空"`
	ClusterName             string `json:"clusterName" binding:"required" msg:"clusterName 字段不能为空"`
	Namespace               string `json:"namespace" binding:"required" msg:"namespace 字段不能为空"`
	Enable                  bool   `json:"enable"`
	LoadBalancerID          string `json:"loadBalancerId" binding:"required" msg:"loadBalancerId 字段不能为空"`
	commentity.BKAdditional `json:",inline"`
}
