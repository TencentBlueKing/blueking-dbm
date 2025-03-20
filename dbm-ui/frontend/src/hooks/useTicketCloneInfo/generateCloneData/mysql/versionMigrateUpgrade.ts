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
import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
import { getTendbhaList } from '@services/source/tendbha';

import { random } from '@utils';

// MySQL 迁移升级
export async function generateMysqlVersionMigrateUpgradeCloneData(ticketData: TicketModel<Mysql.MigrateUpgrade>) {
  const { backup_source: backupSource, clusters, force, infos } = ticketData.details;
  const clusterListResult = await getTendbhaList({
    cluster_ids: infos.map((item) => item.cluster_ids[0]),
    limit: -1,
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
      clusterData: {
        cloudId: clusters[clusterId].bk_cloud_id,
        clusterId,
        clusterType: clusters[clusterId].cluster_type,
        currentVersion: clusters[clusterId].major_version,
        domain: clusters[clusterId].immute_domain,
        masterSlaveList: [
          ...clusterListMap[clusterId].masters,
          ...clusterListMap[clusterId].slaves.filter((item) => item.is_stand_by),
        ].map((item) => ({
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          ip: item.ip,
        })),
        moduleId: clusters[clusterId].db_module_id,
        moduleName: item.display_info.current_module_name,
        packageVersion: clusterListMap[clusterId].masters[0].version,
        readonlySlaveList: clusterListMap[clusterId].slaves
          .filter((item) => !item.is_stand_by)
          .map((item) => ({
            bk_biz_id: item.bk_biz_id,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            ip: item.ip,
          })),
      },
      isLoading: false,
      masterHostData: item.new_master,
      readonlyHostData: (item.read_only_slaves || []).map((readonlySlaveItem) => readonlySlaveItem.new_slave),
      rowKey: random(),
      slaveHostData: item.new_slave,
      targetModule: item.new_db_module_id,
      targetPackage: item.pkg_id,
      targetVersion: item.display_info.target_version,
    };
  });

  return Promise.resolve({
    backupSource,
    force,
    remark: ticketData.remark,
    tableList,
  });
}
