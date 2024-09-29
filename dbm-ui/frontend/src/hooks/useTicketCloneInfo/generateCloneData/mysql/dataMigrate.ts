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
import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

import { random } from '@utils';

// MySQL DB克隆
export function generateMysqlDataMigrateCloneData(ticketData: TicketModel<Mysql.DataMigrate>) {
  const { clusters, infos } = ticketData.details;
  const tableDataList = infos.map((item) => {
    const sourceClusterInfo = clusters[item.source_cluster];
    return {
      rowKey: random(),
      clusterData: {
        id: item.source_cluster,
        domain: sourceClusterInfo.immute_domain,
        type: sourceClusterInfo.cluster_type,
      },
      cloneType: item.data_schema_grant,
      targetClusters: item.target_clusters.map((id) => clusters[id].immute_domain).join(','),
    };
  });
  return Promise.resolve({ tableDataList });
}
