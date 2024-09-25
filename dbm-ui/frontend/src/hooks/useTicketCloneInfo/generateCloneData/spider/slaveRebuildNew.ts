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
import type { SpiderSlaveRebuid } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbclusterMachineList } from '@services/source/tendbcluster';

import { random } from '@utils';

// spider 重建从库-新机重建
export async function generateSpiderSlaveRebuildNewCloneData(ticketData: TicketModel<SpiderSlaveRebuid>) {
  const { infos, backup_source } = ticketData.details;
  const slaveMachineResult = await getTendbclusterMachineList({
    ip: infos.map((item) => item.old_slave.ip).join(','),
    instance_role: 'remote_slave',
  });
  const slaveMachineMap = slaveMachineResult.results.reduce<Record<string, TendbclusterMachineModel>>((obj, item) => {
    Object.assign(obj, {
      [item.ip]: item,
    });
    return obj;
  }, {});

  const tableDataList = infos.map((item) => {
    const slaveMachineItem = slaveMachineMap[item.old_slave.ip];
    return {
      rowKey: random(),
      isLoading: false,
      oldSlave: {
        bkCloudId: slaveMachineItem.bk_cloud_id,
        bkCloudName: slaveMachineItem.bk_cloud_name,
        bkHostId: slaveMachineItem.bk_host_id,
        ip: item.old_slave.ip,
        domian: slaveMachineItem.related_clusters[0].immute_domain,
        clusterId: slaveMachineItem.related_clusters[0].id,
        specConfig: item.resource_spec.new_slave,
        slaveInstanceList: slaveMachineItem.related_instances,
      },
    };
  });

  return {
    tableDataList,
    formData: {
      remark: ticketData.remark,
      backup_source,
    },
  };
}
