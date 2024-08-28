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
import type { RedisProxyScaleUpDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 接入层扩容
export async function generateRedisProxyScaleUpCloneData(ticketData: TicketModel<RedisProxyScaleUpDetails>) {
  const { clusters, infos, specs } = ticketData.details;
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

  return {
    tableDataList: infos.map((item) => ({
      rowKey: random(),
      isLoading: false,
      cluster: clusters[item.cluster_id].immute_domain,
      clusterId: item.cluster_id,
      bkCloudId: item.bk_cloud_id,
      nodeType: 'Proxy',
      targetNum: `${item.target_proxy_count}`,
      spec: {
        ...specs[item.resource_spec.proxy.spec_id],
        count: clusterListMap[item.cluster_id].proxy.length,
      },
      rowModelData: clusterListMap[item.cluster_id],
      cluster_type_name: clusterListMap[item.cluster_id].cluster_type_name,
      selectedSpecId: item.resource_spec.proxy.spec_id,
    })),
    remark: ticketData.remark,
  };
}
