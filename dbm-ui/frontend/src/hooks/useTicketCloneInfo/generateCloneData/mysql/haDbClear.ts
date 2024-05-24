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
import type { MySQLHATruncateDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL 高可用清档
export function generateMysqlDbClearCloneData(ticketData: TicketModel<MySQLHATruncateDetails>) {
  const { clusters, infos } = ticketData.details;
  const tableDataList = infos.map((item) => ({
    cluster_id: item.cluster_id,
    cluster_domain: clusters[item.cluster_id].immute_domain,
    cluster_type: clusters[item.cluster_id].cluster_type,
    db_patterns: item.db_patterns,
    ignore_dbs: item.ignore_dbs,
    ignore_tables: item.ignore_tables,
    table_patterns: item.table_patterns,
    truncate_data_type: item.truncate_data_type,
    uniqueId: random(),
  }));
  return Promise.resolve({
    tableDataList,
    remark: ticketData.remark,
  });
}
