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
import type { RedisVersionUpgrade } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 版本升级
export async function generateRedisRedisVersionUpgradeCloneData(ticketData: TicketModel<RedisVersionUpgrade>) {
  const { infos } = ticketData.details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_ids[0]).join(','),
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

  const tableDataList = infos.map((infoItem) => {
    const clusterItem = clusterListMap[infoItem.cluster_ids[0]];
    return {
      rowKey: random(),
      isLoading: false,
      cluster: clusterItem.master_domain,
      clusterId: infoItem.cluster_ids[0],
      nodeType: infoItem.node_type,
      clusterType: clusterItem.cluster_spec.spec_cluster_type,
      targetVersion: infoItem.target_version,
    };
  });

  return {
    tableDataList,
  };
}
