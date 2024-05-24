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
import type { MySQLRestoreLocalSlaveDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL 重建从库-原地重建
export function generateMysqlRestoreLocalSlaveCloneData(ticketData: TicketModel<MySQLRestoreLocalSlaveDetails>) {
  const { infos } = ticketData.details;
  const tableDataList = infos.map((item) => ({
    rowKey: random(),
    slave: {
      bkCloudId: item.slave.bk_cloud_id,
      bkHostId: item.slave.bk_host_id,
      ip: item.slave.ip,
      port: item.slave.port,
      instanceAddress: `${item.slave.ip}:${item.slave.port}`,
      clusterId: item.cluster_id,
    },
  }));
  return Promise.resolve({
    backupType: ticketData.details.backup_source,
    tableDataList,
    remark: ticketData.remark,
  });
}
