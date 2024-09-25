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

import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';
import type { SpiderMigrateCluster } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbclusterMachineList } from '@services/source/tendbcluster';

import { random } from '@utils';

// spider 迁移主从
export async function generateSpiderMasterSlaveCloneCloneData(ticketData: TicketModel<SpiderMigrateCluster>) {
  const { infos, backup_source: backupSource } = ticketData.details;
  const masterMachineResult = await getTendbclusterMachineList({
    ip: infos.map((item) => item.old_master.ip).join(','),
    instance_role: 'remote_master',
  });
  const masterMachineMap = masterMachineResult.results.reduce<Record<string, TendbclusterMachineModel>>((obj, item) => {
    Object.assign(obj, {
      [item.ip]: item,
    });
    return obj;
  }, {});

  const tableDataList = infos.map((item) => {
    const masterItem = masterMachineMap[item.old_master.ip];
    return {
      rowKey: random(),
      isLoading: false,
      clusterData: {
        ip: item.old_master.ip,
        clusterId: item.cluster_id,
        domain: masterItem.related_clusters[0].immute_domain,
        cloudId: masterItem.bk_cloud_id,
        cloudName: masterItem.bk_cloud_name,
        hostId: item.old_master.bk_host_id,
      },
      masterInstanceList: masterItem.related_instances,
      newHostList: [item.new_master.ip, item.new_slave.ip],
    };
  });

  return Promise.resolve({
    tableDataList,
    backupSource,
    remark: ticketData.remark,
  });
}
