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
import type { RedisProxyScaleDownDetails } from '@services/model/ticket/details/redis';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 接入层缩容
export async function generateRedisProxyScaleDownCloneData(details: RedisProxyScaleDownDetails) {
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

  return infos.map((item) => {
    const clusterId = item.cluster_id;
    return {
      rowKey: random(),
      isLoading: false,
      cluster: clusters[clusterId].immute_domain,
      clusterId,
      bkCloudId: clusterListMap[clusterId].bk_cloud_id,
      nodeType: 'Proxy',
      spec: {
        ...clusterListMap[clusterId].proxy[0].spec_config,
        name: clusterListMap[clusterId].cluster_spec.spec_name,
        id: clusterListMap[clusterId].cluster_spec.spec_id,
        count: clusterListMap[clusterId].proxy.length,
      },
      targetNum: `${clusterListMap[clusterId].proxy.length}`,
    };
  });
}
