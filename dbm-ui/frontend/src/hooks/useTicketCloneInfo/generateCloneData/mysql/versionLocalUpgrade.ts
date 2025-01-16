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
import TendbsingleModel from '@services/model/mysql/tendbsingle';
import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
import { getTendbhaList } from '@services/source/tendbha';
import { getTendbsingleList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

import { random } from '@utils';

// MySQL 原地升级
export async function generateMysqlVersionLocalUpgradeCloneData(ticketData: TicketModel<Mysql.LocalUpgrade>) {
  const { clusters, infos, force } = ticketData.details;
  const clusterType = infos[0].display_info.cluster_type;
  const apiMap = {
    [ClusterTypes.TENDBSINGLE]: getTendbsingleList,
    [ClusterTypes.TENDBHA]: getTendbhaList,
  };
  const clusterListResult = await apiMap[clusterType as keyof typeof apiMap]({
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
    {} as Record<number, TendbhaModel | TendbsingleModel>,
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
        moduleId: clusters[clusterId].db_module_id,
        cloudId: clusters[clusterId].bk_cloud_id,
      },
      targetVersion: item.display_info.target_version,
      targetPackage: item.pkg_id,
      targetModule: item.new_db_module_id,
    };
  });

  return Promise.resolve({ tableList, remark: ticketData.remark, force });
}
