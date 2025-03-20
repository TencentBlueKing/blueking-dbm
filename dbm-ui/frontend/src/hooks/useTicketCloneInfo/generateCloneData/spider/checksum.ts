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

// Spider Checksum
export function generateSpiderChecksumCloneData(ticketData: TicketModel<TendbCluster.CheckSum>) {
  const { details, remark } = ticketData;
  const { clusters, infos } = details;
  const tableDataList = infos.map((item) => {
    const clusterInfo = clusters[item.cluster_id];
    return {
      backupInfos: item.backup_infos.map((backupInfosItem) => {
        const {
          db_patterns: dbPatterns,
          ignore_dbs: ignoreDbs,
          ignore_tables: ignoreTables,
          master,
          slave,
          table_patterns: tablePatterns,
        } = backupInfosItem;
        return {
          dbPatterns,
          ignoreDbs,
          ignoreTables,
          master,
          slave,
          tablePatterns,
        };
      }),
      clusterData: {
        domain: clusterInfo.immute_domain,
        id: item.cluster_id,
      },
      rowKey: random(),
      scope: item.checksum_scope,
    };
  });
  return Promise.resolve({
    formInfo: {
      data_repair: details.data_repair,
      is_sync_non_innodb: details.is_sync_non_innodb,
      remark,
      runtime_hour: details.runtime_hour,
      timing: new Date(details.timing),
    },
    tableDataList,
  });
}
