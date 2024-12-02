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
import type { RedisInstallModuleDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Redis 安装Module
export function generateRedisInstallModule(ticketData: TicketModel<RedisInstallModuleDetails>) {
  const { clusters, infos } = ticketData.details;
  return Promise.resolve({
    tableDataList: infos.map((info) => {
      const cluster = clusters[info.cluster_id];
      return {
        rowKey: random(),
        isLoading: false,
        srcCluster: cluster.immute_domain,
        clusterId: info.cluster_id,
        bkCloudId: cluster.bk_cloud_id,
        clusterType: cluster.cluster_type,
        clusterTypeName: cluster.cluster_type_name,
        dbVersion: info.db_version,
        loadModules: info.load_modules,
      };
    }),
    remark: ticketData.remark,
  });
}
