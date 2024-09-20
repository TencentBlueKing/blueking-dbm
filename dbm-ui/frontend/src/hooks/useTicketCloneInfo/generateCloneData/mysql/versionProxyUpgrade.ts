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

import type { MySQLProxyUpgradeDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL Proxy 升级
export function generateMysqlVersionProxyUpgradeCloneData(ticketData: TicketModel<MySQLProxyUpgradeDetails>) {
  const { clusters, infos } = ticketData.details;
  const tableList = infos.map((item) => {
    const clusterId = item.cluster_ids[0];
    return {
      rowKey: random(),
      isLoading: false,
      clusterData: {
        domain: clusters[clusterId].immute_domain,
        clusterId,
        clusterType: clusters[clusterId].cluster_type,
        currentVersion: item.display_info.current_version,
      },
      targetVersion: item.pkg_id,
    };
  });

  return Promise.resolve({ tableList, remark: ticketData.remark });
}
