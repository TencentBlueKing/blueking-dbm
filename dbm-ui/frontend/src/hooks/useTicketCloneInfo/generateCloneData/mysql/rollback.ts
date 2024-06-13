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
import type { MySQLRollbackDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL 定点构造
export function generateMysqlRollbackCloneData(ticketData: TicketModel<MySQLRollbackDetails>) {
  const { clusters, infos } = ticketData.details;
  const tableDataList = infos.map((item) => ({
    rowKey: random(),
    clusterData: {
      id: item.cluster_id,
      domain: clusters[item.cluster_id].immute_domain,
      cloudId: clusters[item.cluster_id].bk_cloud_id,
    },
    rollbackIp: item.rollback_ip,
    backupSource: item.backup_source,
    backupid: item.backupid,
    rollbackTime: item.rollback_time,
    databases: item.databases,
    databasesIgnore: item.databases_ignore,
    tables: item.tables,
    tablesIgnore: item.tables_ignore,
  }));
  return Promise.resolve({
    tableDataList,
    remark: ticketData.remark,
  });
}
