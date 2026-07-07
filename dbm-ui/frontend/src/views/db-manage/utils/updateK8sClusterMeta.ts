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
import { updateQdrantHaClusterMeta } from '@services/source/qdrantHa';
import { updateSurrealdbHaClusterMeta } from '@services/source/surrealdbHa';
import { updateSurrealdbSingleClusterMeta } from '@services/source/surrealdbSingle';

import { ClusterTypes } from '@common/const';

export type UpdateClusterMetaFn = typeof updateQdrantHaClusterMeta;

export type UpdateClusterMetaParams = ServiceParameters<UpdateClusterMetaFn>;

// 使用统一 update_cluster_meta 接口的集群类型映射
const CLUSTER_META_UPDATER_MAP: Partial<Record<ClusterTypes, UpdateClusterMetaFn>> = {
  [ClusterTypes.K8S_QDRANT_HA]: updateQdrantHaClusterMeta,
  [ClusterTypes.K8S_SURREALDB_HA]: updateSurrealdbHaClusterMeta,
  [ClusterTypes.K8S_SURREALDB_SINGLE]: updateSurrealdbSingleClusterMeta,
};

/**
 * 根据集群类型获取元数据（别名 / 标签）更新函数
 * 若集群类型未接入统一 update_cluster_meta 接口则返回 undefined
 */
export const getClusterMetaUpdater = (clusterType: string) =>
  CLUSTER_META_UPDATER_MAP[clusterType as keyof typeof CLUSTER_META_UPDATER_MAP];
