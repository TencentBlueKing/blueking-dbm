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
import type { RedisClusterShardUpdateDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisList } from '@services/source/redis';

import { random } from '@utils';

import { t } from '@locales/index';

// Redis 集群分片数变更
export async function generateRedisClusterShardUpdateCloneData(
  ticketData: TicketModel<RedisClusterShardUpdateDetails>,
) {
  const { clusters, infos } = ticketData.details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.src_cluster).join(','),
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

  const tableData = infos.map((item) => {
    const currentClusterInfo = clusterListMap[item.src_cluster];
    return {
      rowKey: random(),
      isLoading: false,
      srcCluster: clusters[item.src_cluster].immute_domain,
      clusterId: item.src_cluster,
      bkCloudId: currentClusterInfo.bk_cloud_id,
      switchMode: t('需人工确认'),
      currentCapacity: {
        used: 1,
        total: currentClusterInfo.cluster_capacity,
      },
      currentSepc: `${currentClusterInfo.cluster_capacity}G_${currentClusterInfo.cluster_spec.qps.max}/s（${currentClusterInfo.cluster_shard_num} 分片）`,
      clusterType: currentClusterInfo.cluster_spec.spec_cluster_type,
      clusterTypeName: currentClusterInfo.cluster_type_name,
      currentShardNum: currentClusterInfo.cluster_shard_num,
      currentSpecId: currentClusterInfo.cluster_spec.spec_id,
      dbVersion: item.db_version,
      specConfig: {
        cpu: currentClusterInfo.cluster_spec.cpu,
        id: currentClusterInfo.cluster_spec.spec_id,
        mem: currentClusterInfo.cluster_spec.mem,
        qps: currentClusterInfo.cluster_spec.qps,
      },
      proxy: {
        id: currentClusterInfo.proxy[0].spec_config.id,
        count: new Set(currentClusterInfo.proxy.map((item) => item.ip)).size,
      },
    };
  });
  return {
    tableList: tableData,
    type: ticketData.details.data_check_repair_setting.type,
    frequency: ticketData.details.data_check_repair_setting.execution_frequency,
    remark: ticketData.remark,
  };
}
