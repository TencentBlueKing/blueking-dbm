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
import RedisModel from '@services/model/redis/redis';
import type { RedisDataStructrueDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 定点构造
export async function generateRedisDataStructureCloneData(ticketData: TicketModel<RedisDataStructrueDetails>) {
  const { infos } = ticketData.details;
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

  return Promise.resolve({
    tableDataList: infos.map((item) => {
      const currentClusterInfo = clusterListMap[item.cluster_id];
      const instances = currentClusterInfo.redis_master.map((row) => `${row.ip}:${row.port}`);
      return {
        rowKey: random(),
        isLoading: false,
        cluster: currentClusterInfo.master_domain,
        clusterType: currentClusterInfo.cluster_type,
        clusterTypeName: currentClusterInfo.cluster_type_name,
        clusterId: item.cluster_id,
        bkCloudId: item.bk_cloud_id,
        hostNum: `${item.resource_spec.redis.count}`,
        targetDateTime: item.recovery_time_point,
        instances,
        spec: {
          ...currentClusterInfo.cluster_spec,
          name: currentClusterInfo.cluster_spec.spec_name,
          id: currentClusterInfo.cluster_spec.spec_id,
        },
      };
    }),
    remark: ticketData.remark,
  });
}
