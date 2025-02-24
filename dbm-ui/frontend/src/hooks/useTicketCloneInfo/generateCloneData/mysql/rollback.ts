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
import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL 定点构造
export function generateMysqlRollbackCloneData(ticketData: TicketModel<Mysql.RollbackCluster>) {
  const { clusters, infos } = ticketData.details;
  const tableDataList = infos.map((item) => ({
    backupid: item.backupinfo.backup_id,
    backupSource: item.backup_source,
    clusterData: {
      cloudId: clusters[item.cluster_id].bk_cloud_id,
      domain: clusters[item.cluster_id].immute_domain,
      id: item.cluster_id,
    },
    databases: item.databases,
    databasesIgnore: item.databases_ignore,
    rollbackHost: item.rollback_host,
    rollbackTime: item.rollback_time,
    rollbackType: `${item.backup_source?.toLocaleUpperCase()}_AND_${item.backupinfo.backup_id ? 'BACKUPID' : 'TIME'}`,
    rowKey: random(),
    tables: item.tables,
    tablesIgnore: item.tables_ignore,
    targetClusterId: item.target_cluster_id,
  }));
  return Promise.resolve({
    remark: ticketData.remark,
    rollback_cluster_type: ticketData.details.rollback_cluster_type,
    tableDataList,
  });
}
