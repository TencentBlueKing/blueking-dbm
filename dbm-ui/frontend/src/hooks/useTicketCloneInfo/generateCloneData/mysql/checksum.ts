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
import TendbhaModel from '@services/model/mysql/tendbha';
import type { MySQLChecksumDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbhaList } from '@services/source/tendbha';

import { random } from '@utils';

// Mysql SQL变更执行
export async function generateMysqlChecksumCloneData(ticketData: TicketModel<MySQLChecksumDetails>) {
  const { details, remark } = ticketData;
  const clustersResult = await getTendbhaList({
    cluster_ids: details.infos.map((item) => item.cluster_id),
    limit: -1,
    offset: 0,
  });
  const clusters = clustersResult.results.reduce(
    (results, item) => {
      Object.assign(results, {
        [item.id]: item,
      });
      return results;
    },
    {} as Record<number, TendbhaModel>,
  );

  const tableDataList = details.infos.map((item) => {
    const masterInfo = clusters[item.cluster_id].masters[0];
    return {
      rowKey: random(),
      isLoading: false,
      clusterData: {
        id: item.cluster_id,
        domain: clusters[item.cluster_id].master_domain,
      },
      dbPatterns: item.db_patterns,
      ignoreDbs: item.ignore_dbs,
      tablePatterns: item.table_patterns,
      ignoreTables: item.ignore_tables,
      master: masterInfo ? `${masterInfo.ip}:${masterInfo.port}` : '',
      masterInstance: masterInfo,
      slaves: item.slaves.map((slave) => `${slave.ip}:${slave.port}`),
      slaveList: clusters[item.cluster_id].slaves || [],
    };
  });
  return {
    tableDataList,
    timing: new Date(details.timing),
    runtime_hour: details.runtime_hour,
    data_repair: details.data_repair,
    remark,
  };
}
