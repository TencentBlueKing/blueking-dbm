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
import RedisModel, { RedisClusterTypes } from '@services/model/redis/redis';
import type { RedisScaleUpDownDetails } from '@services/model/ticket/details/redis';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 集群容量变更
export async function generateRedisScaleUpdownCloneData(details: RedisScaleUpDownDetails) {
  const { clusters, infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_id).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  return infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    targetCluster: clusters[item.cluster_id].immute_domain,
    currentSepc: clusterListMap[item.cluster_id].cluster_spec.spec_name,
    clusterId: item.cluster_id,
    bkCloudId: item.bk_cloud_id,
    shardNum: item.shard_num,
    groupNum: item.group_num,
    version: item.db_version,
    clusterType: clusters[item.cluster_id].cluster_type as RedisClusterTypes,
    currentCapacity: {
      used: 1,
      total: clusterListMap[item.cluster_id].cluster_capacity,
    },
    switchMode: item.online_switch_type,
  }));
}
