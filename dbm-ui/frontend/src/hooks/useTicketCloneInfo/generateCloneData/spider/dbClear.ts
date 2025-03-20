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

import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

import { random } from '@utils';

// Spider tendbcluster 清档
export function generateSpiderDbClearCloneData(ticketData: TicketModel<TendbCluster.TruncateData>) {
  const { clusters, infos } = ticketData.details;
  const tableDataList = infos.map((item) => {
    const clusterItem = clusters[item.cluster_id];
    return {
      clusterData: {
        domain: clusterItem.immute_domain,
        id: clusterItem.id,
      },
      dbPatterns: item.db_patterns,
      ignoreDbs: item.ignore_dbs,
      ignoreTables: item.ignore_tables,
      rowKey: random(),
      tablePatterns: item.table_patterns,
      truncateDataType: item.truncate_data_type,
    };
  });

  return Promise.resolve({
    clear_mode: ticketData.details.clear_mode,
    isSafe: !infos[0].force,
    remark: ticketData.remark,
    tableDataList,
  });
}
