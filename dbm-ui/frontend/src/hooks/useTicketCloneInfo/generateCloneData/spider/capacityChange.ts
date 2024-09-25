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

import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
import type { SpiderNodeRebalanceDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbClusterList } from '@services/source/tendbcluster';

import { random } from '@utils';

// Spider 集群remote节点扩缩容
export async function generateSpiderCapacityChangeCloneData(ticketData: TicketModel<SpiderNodeRebalanceDetails>) {
  const {
    infos,
    need_checksum: needChecksum,
    trigger_checksum_type: triggerChecksumType,
    trigger_checksum_time: triggerChecksumTime,
    backup_source: backupSource,
  } = ticketData.details;
  const clusterListResult = await getTendbClusterList({
    cluster_ids: infos.map((item) => item.cluster_id),
  });
  const clusterListMap = clusterListResult.results.reduce<Record<number, TendbclusterModel>>((obj, item) => {
    Object.assign(obj, {
      [item.id]: item,
    });
    return obj;
  }, {});

  const tableDataList = infos.map((item) => {
    const clusterItem = clusterListMap[item.cluster_id];
    const specItem = clusterItem.spider_master[0].spec_config;
    return {
      rowKey: random(),
      clusterData: {
        bkCloudId: clusterItem.bk_cloud_id,
        clusterCapacity: clusterItem.cluster_capacity,
        clusterShardNum: clusterItem.cluster_shard_num,
        clusterSpec: {
          spec_name: clusterItem.cluster_spec.spec_name,
        },
        dbModuleId: clusterItem.db_module_id,
        id: clusterItem.id,
        machinePairCnt: clusterItem.machine_pair_cnt,
        masterDomain: clusterItem.master_domain,
      },
      resourceSpec: {
        id: specItem.id,
        name: specItem.name,
      },
      resource_spec: {
        ...item.resource_spec,
        remote_shard_num: item.remote_shard_num,
      },
    };
  });

  return {
    backupSource,
    needChecksum,
    triggerChecksumType,
    triggerChecksumTime,
    tableDataList,
    remark: ticketData.remark,
  };
}
