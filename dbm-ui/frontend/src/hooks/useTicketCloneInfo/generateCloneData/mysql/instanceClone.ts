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

import type { MySQLInstanceCloneDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { checkMysqlInstances } from '@services/source/instances';

import { random } from '@utils';

type InstanceInfo = ServiceReturnType<typeof checkMysqlInstances>[number];

// Mysql DB实例权限克隆
export async function generateMysqlInstanceCloneData(ticketData: TicketModel<MySQLInstanceCloneDetails>) {
  const instanceList = _.flatMap(ticketData.details.clone_data.map((item) => [item.source, item.target]));
  const instanceListInfos = await checkMysqlInstances({
    bizId: ticketData.bk_biz_id,
    instance_addresses: instanceList,
  });
  const instanceInfoMap = instanceListInfos.reduce<Record<string, InstanceInfo>>(
    (results, item) =>
      Object.assign(results, {
        [item.instance_address]: item,
      }),
    {},
  );
  const tableDataList = ticketData.details.clone_data.map((item) => {
    const sourceInstance = instanceInfoMap[item.source];
    const targetInstance = instanceInfoMap[item.target];
    return {
      rowKey: random(),
      source: {
        bkCloudId: sourceInstance.bk_cloud_id,
        clusterId: sourceInstance.cluster_id,
        dbModuleId: sourceInstance.db_module_id,
        dbModuleName: sourceInstance.db_module_name,
        instanceAddress: sourceInstance.instance_address,
        masterDomain: sourceInstance.master_domain,
        clusterType: sourceInstance.cluster_type,
      },
      target: {
        cluster_id: targetInstance.cluster_id,
        bk_host_id: targetInstance.bk_host_id,
        bk_cloud_id: targetInstance.bk_cloud_id,
        port: targetInstance.port,
        ip: targetInstance.ip,
        instance_address: targetInstance.instance_address,
      },
    };
  });
  return Promise.resolve({
    tableDataList,
    remark: ticketData.remark,
  });
}
