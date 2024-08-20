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

import TendbInstanceModel from '@services/model/spider/tendbInstance';
import type { MySQLInstanceCloneDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { getSpiderInstanceList } from '@services/source/spider';

import { random } from '@utils';

// Spider 权限克隆
export async function generateSpiderPrivilegeCloneInstCloneData(ticketData: TicketModel<MySQLInstanceCloneDetails>) {
  const { clone_data: cloneData } = ticketData.details;
  const instanceListResult = await getSpiderInstanceList({
    instance_address: cloneData.reduce((prev, item) => [...prev, item.source, item.target], [] as string[]).join(','),
  });
  const instanceListMap = instanceListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.instance_address]: item,
      });
      return obj;
    },
    {} as Record<string, TendbInstanceModel>,
  );

  return {
    tableDataList: ticketData.details.clone_data.map((item) => {
      const sourceInfo = instanceListMap[item.source];
      const targetInfo = instanceListMap[item.target];
      return {
        rowKey: random(),
        source: {
          bkCloudId: sourceInfo.bk_cloud_id,
          clusterId: sourceInfo.cluster_id,
          dbModuleId: sourceInfo.db_module_id,
          dbModuleName: item.module,
          instanceAddress: item.source,
          masterDomain: sourceInfo.master_domain,
        },
        target: {
          cluster_id: targetInfo.cluster_id,
          bk_host_id: targetInfo.bk_host_id,
          bk_cloud_id: targetInfo.bk_cloud_id,
          port: targetInfo.port,
          ip: targetInfo.ip,
          instance_address: item.target,
        },
      };
    }),
    remark: ticketData.remark,
  };
}
