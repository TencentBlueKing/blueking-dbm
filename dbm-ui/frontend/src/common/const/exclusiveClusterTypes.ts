/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import { ClusterTypes } from './clusterTypes';

/**
 * 允许申请独占集群（独立 BCS 集群资源）的集群类型白名单
 * 与后端 isPublic=false 的生效范围保持一致
 */
export const exclusiveClusterTypeWhitelist: ClusterTypes[] = [
  ClusterTypes.K8S_QDRANT_HA,
  ClusterTypes.K8S_SURREALDB_HA,
  ClusterTypes.K8S_SURREALDB_SINGLE,
];

/**
 * 判断集群类型是否允许申请独占集群
 */
export const isExclusiveClusterType = (clusterType?: string) =>
  exclusiveClusterTypeWhitelist.includes(clusterType as ClusterTypes);
