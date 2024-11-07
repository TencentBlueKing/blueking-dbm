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
import type { RedisClusterMigrate } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Redis 集群迁移
export async function generateRedisMigrateClusterCloneData(ticketData: TicketModel<RedisClusterMigrate>) {
  const { infos, clusters, specs } = ticketData.details;
  const tableDataList = infos.map((infoItem) => {
    const clusterItem = clusters[infoItem.cluster_id];
    const specItem = specs[infoItem.resource_spec.backend_group.spec_id];
    return {
      rowKey: random(),
      isLoading: false,
      spanData: {
        isStart: false,
        isGeneral: true,
        rowSpan: 1,
      },
      clusterData: {
        instance: infoItem.display_info.instance,
        domain: clusterItem.immute_domain,
        clusterId: clusterItem.id,
        clusterType: clusterItem.cluster_type,
        specId: specItem.id,
        specName: specItem.name,
      },
      master: infoItem.old_nodes.master[0],
      slave: infoItem.old_nodes.slave[0],
    };
  });

  return {
    tableDataList,
    remark: ticketData.remark,
  };
}
