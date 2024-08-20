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

import type { SpiderRollbackDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// spider 定点回档
export function generateSpiderRollbackCloneData(ticketData: TicketModel<SpiderRollbackDetails>) {
  const tableDataList = [ticketData.details].map((item) => {
    const clusterItem = ticketData.details.clusters[item.cluster_id];
    return {
      rowKey: random(),
      isLoading: false,
      clusterData: {
        id: clusterItem.id,
        domain: clusterItem.immute_domain,
        cloudId: clusterItem.bk_cloud_id,
      },
      rollbackupType: item.rollback_type,
      rollbackTime: item.rollback_time,
      databases: item.databases,
      databasesIgnore: item.databases_ignore,
      tables: item.tables,
      tablesIgnore: item.tables_ignore,
    };
  });

  return Promise.resolve({
    tableDataList,
    remark: ticketData.remark,
  });
}
