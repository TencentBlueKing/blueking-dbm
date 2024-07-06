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
import type { RedisDBReplaceDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Redis 整机替换
export function generateRedisClusterCutoffCloneData(ticketData: TicketModel<RedisDBReplaceDetails>) {
  const { clusters, infos, specs } = ticketData.details;
  return Promise.resolve({
    tableDataList: infos.reduce(
      (dataList, item) => {
        const roleList = ['proxy', 'redis_master', 'redis_slave'] as ['proxy', 'redis_master', 'redis_slave'];
        const roleMap = {
          redis_master: 'master',
          redis_slave: 'slave',
          proxy: 'proxy',
        };
        roleList.forEach((role) => {
          if (item[role].length > 0) {
            item[role].forEach((info) => {
              dataList.push({
                rowKey: random(),
                isLoading: false,
                ip: info.ip,
                role: roleMap[role],
                clusterIds: item.cluster_ids,
                bkCloudId: item.bk_cloud_id,
                cluster: {
                  domain: item.cluster_ids.map((id) => clusters[id].immute_domain).join(','),
                  isStart: false,
                  isGeneral: true,
                  rowSpan: 1,
                },
                spec: specs[info.spec_id],
              });
            });
          }
        });
        return dataList;
      },
      [] as {
        rowKey: string;
        isLoading: boolean;
        ip: string;
        role: string;
        clusterIds: number[];
        bkCloudId: number;
        cluster: any;
        spec: any;
      }[],
    ),
    remark: ticketData.remark,
  });
}
