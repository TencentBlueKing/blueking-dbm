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

import type { SpiderRenameDatabaseDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Spider Tendbcluster 重命名
export function generateSpiderDbRenameCloneData(ticketData: TicketModel<SpiderRenameDatabaseDetails>) {
  const { infos, force, clusters } = ticketData.details;
  const tableDataList = infos.map((item) => {
    const clusterItem = clusters[item.cluster_id];
    return {
      rowKey: random(),
      clusterData: {
        id: item.cluster_id,
        domain: clusterItem.immute_domain,
      },
      fromDatabase: item.from_database,
      toDatabase: item.to_database,
    };
  });

  return Promise.resolve({
    tableDataList,
    force,
    remark: ticketData.remark,
  });
}
