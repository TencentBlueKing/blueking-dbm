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
import type { RedisSingleMigrate } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Redis 主从迁移
export async function generateRedisMigrateSingleCloneData(ticketData: TicketModel<RedisSingleMigrate>) {
  const { infos, clusters } = ticketData.details;
  const isDomain = infos[0].display_info.migrate_type === 'domain';
  const mapKey = isDomain ? 'domain' : 'ip';

  const rowMap = infos.reduce<Record<string, RedisSingleMigrate['infos']>>((prevMap, infoItem) => {
    if (prevMap[infoItem.display_info[mapKey]]) {
      return Object.assign({}, prevMap, {
        [infoItem.display_info[mapKey]]: prevMap[infoItem.display_info[mapKey]].concat(infoItem),
      });
    }
    return Object.assign({}, prevMap, {
      [infoItem.display_info[mapKey]]: [infoItem],
    });
  }, {});
  const tableDataList = Object.values(rowMap).map((infoList) => {
    const rowItem = infoList[0];
    const clusterItem = clusters[rowItem.cluster_id];
    const relatedInstanceList = infoList.map((infoItem) => {
      const masterItem = infoItem.old_nodes.master[0];
      return {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: masterItem.bk_cloud_id,
        bk_host_id: masterItem.bk_host_id,
        ip: masterItem.ip,
        port: masterItem.port,
        instance: `${masterItem.ip}:${masterItem.port}`,
      };
    });

    const clusterData = isDomain
      ? {
          domain: rowItem.display_info.domain,
          cloudId: clusterItem.bk_cloud_id,
          clusterType: clusterItem.cluster_type,
          clusterId: rowItem.cluster_id,
          relatedInstance: relatedInstanceList,
        }
      : {
          ip: rowItem.display_info.ip,
          cloudId: clusterItem.bk_cloud_id,
          clusterType: clusterItem.cluster_type,
          relatedInstance: relatedInstanceList,
        };
    return {
      rowKey: random(),
      isLoading: false,
      clusterData,
      targetSpecId: rowItem.resource_spec.backend_group.spec_id,
      targetVersion: rowItem.db_version,
    };
  });
  return {
    tableDataList,
    remark: ticketData.remark,
    isDomain,
  };
}
