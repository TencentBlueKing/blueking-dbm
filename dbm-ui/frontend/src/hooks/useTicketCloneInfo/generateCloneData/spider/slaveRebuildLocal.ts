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

import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
import type { SpiderSlaveRebuid } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbclusterInstanceList } from '@services/source/tendbcluster';

import { random } from '@utils';

// spider 重建从库-本地重建
export async function generateSpiderSlaveRebuildLocalCloneData(ticketData: TicketModel<SpiderSlaveRebuid>) {
  const { infos, backup_source } = ticketData.details;
  const instanceListResult = await getTendbclusterInstanceList({
    instance: infos.map((item) => item.slave.ip),
    role: 'remote_slave',
  });
  const instanceMap = instanceListResult.results.reduce<Record<string, TendbclusterInstanceModel>>((obj, item) => {
    Object.assign(obj, {
      [item.ip]: item,
    });
    return obj;
  }, {});

  const tableDataList = infos.map((item) => {
    const instanceItem = instanceMap[item.slave.ip];

    return {
      rowKey: random(),
      isLoading: false,
      slave: {
        bkCloudId: instanceItem.bk_cloud_id,
        bkHostId: instanceItem.bk_host_id,
        ip: instanceItem.ip,
        port: item.slave.port,
        instanceAddress: instanceItem.instance_address,
        clusterId: instanceItem.cluster_id,
        domain: instanceItem.master_domain,
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
