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
import type { MySQLMigrateUpgradeDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbhaList } from '@services/source/tendbha';

import { random } from '@utils';

// MySQL 迁移升级
export async function generateMysqlVersionMigrateUpgradeCloneData(ticketData: TicketModel<MySQLMigrateUpgradeDetails>) {
  const { clusters, infos, backup_source: backupSource } = ticketData.details;
  const clusterListResult = await getTendbhaList({
    id: infos.map((item) => item.cluster_ids[0]).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, TendbhaModel>,
  );
  const tableList = infos.map((item) => {
    const clusterId = item.cluster_ids[0];
    return {
      rowKey: random(),
      isLoading: false,
      clusterData: {
        domain: clusters[clusterId].immute_domain,
        clusterId,
        clusterType: clusters[clusterId].cluster_type,
        currentVersion: clusters[clusterId].major_version,
        packageVersion: clusterListMap[clusterId].masters[0].version,
        moduleName: item.display_info.current_module_name,
        cloudId: clusters[clusterId].bk_cloud_id,
      },
      targetVersion: item.display_info.target_version,
      targetPackage: item.pkg_id,
      targetModule: item.new_db_module_id,
      masterHostData: item.new_master,
      slaveHostData: item.new_slave,
    };
  });

  return Promise.resolve({
    tableList,
    backupSource,
    remark: ticketData.remark,
  });
}
