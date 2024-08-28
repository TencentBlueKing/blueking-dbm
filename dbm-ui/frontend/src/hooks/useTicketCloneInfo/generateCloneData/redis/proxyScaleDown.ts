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

import _ from 'lodash';

import RedisModel from '@services/model/redis/redis';
import RedisInstanceModel from '@services/model/redis/redis-instance';
import type { RedisProxyScaleDownDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisInstances, getRedisList } from '@services/source/redis';

import { random } from '@utils';

// Redis 接入层缩容
export async function generateRedisProxyScaleDownCloneData(ticketData: TicketModel<RedisProxyScaleDownDetails>) {
  const { clusters, infos } = ticketData.details;
  const [clusterListResult, instanceListResult] = await Promise.all([
    getRedisList({
      cluster_ids: infos.map((item) => item.cluster_id).join(','),
    }),
    getRedisInstances({
      ip: _.flatten(infos.map((infoItem) => infoItem.proxy_reduced_hosts?.map((hostItem) => hostItem.ip))).join(','),
    }),
  ]);
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) =>
      Object.assign({}, obj, {
        [item.id]: item,
      }),
    {} as Record<number, RedisModel>,
  );
  const instanceListMap = instanceListResult.results.reduce(
    (obj, item) =>
      Object.assign({}, obj, {
        [item.ip]: item,
      }),
    {} as Record<string, RedisInstanceModel>,
  );

  const formatValue = (data: RedisInstanceModel) => ({
    bk_host_id: data.bk_host_id,
    instance_address: data.instance_address || '',
    cluster_id: data.cluster_id,
    bk_cloud_id: data.bk_cloud_id,
    ip: data.ip || '',
    port: data.port,
    cluster_type: data.cluster_type,
    id: data.id,
    master_domain: data.master_domain,
    bk_cloud_name: data.bk_cloud_name,
    db_module_id: data.db_module_id,
    db_module_name: '',
    cluster_name: '',
  });

  return {
    tableDataList: infos.map((item) => {
      const clusterId = item.cluster_id;
      return {
        rowKey: random(),
        isLoading: false,
        cluster: clusters[clusterId].immute_domain,
        clusterId,
        bkCloudId: clusterListMap[clusterId].bk_cloud_id,
        nodeType: 'Proxy',
        cluster_type_name: clusterListMap[clusterId].cluster_type_name,
        proxyList: clusterListMap[clusterId].proxy,
        selectedNodeList: (item.proxy_reduced_hosts || []).map((proxyHost) =>
          formatValue(instanceListMap[proxyHost.ip]),
        ),
        // targetNum: `${clusterListMap[clusterId].proxy.length}`,
        targetNum: `${clusterListMap[clusterId].proxy.length - (item.target_proxy_count || 0)}`,
        switchMode: item.online_switch_type,
      };
    }),
    remark: ticketData.remark,
  };
}
