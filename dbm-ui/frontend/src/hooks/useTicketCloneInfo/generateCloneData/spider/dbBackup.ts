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

import type { SpiderFullBackupDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Spider TenDBCluster 全备单据
export function generateSpiderDbBackupCloneData(ticketData: TicketModel<SpiderFullBackupDetails>) {
  const { infos, clusters } = ticketData.details;
  const tableDataList = infos.clusters.map((item) => {
    const clusterItem = clusters[item.cluster_id];

    return {
      rowKey: random(),
      clusterData: {
        id: clusterItem.id,
        domain: clusterItem.immute_domain,
      },
      backupLocal: item.backup_local,
    };
  });

  return Promise.resolve({
    tableDataList,
    form: {
      backup_type: infos.backup_type,
      file_tag: infos.file_tag,
      remark: ticketData.remark,
    },
  });
}
