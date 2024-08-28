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
import type { RedisDataCopyDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Redis 集群数据复制
export function generateRedisDataCopyCloneData(ticketData: TicketModel<RedisDataCopyDetails>) {
  const { clusters, infos } = ticketData.details;

  const tableList = infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: clusters[item.src_cluster].immute_domain,
    srcClusterTypeName: clusters[item.src_cluster].cluster_type_name,
    srcClusterId: item.src_cluster,
    clusterType: item.src_cluster_type,
    targetCluster: clusters[item.dst_cluster].immute_domain,
    targetClusterId: item.dst_cluster,
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
    targetBusines: item.dst_bk_biz_id,
    password: item.src_cluster_password,
  }));

  return Promise.resolve({
    tableList,
    copyMode: ticketData.details.dts_copy_type,
    writeMode: ticketData.details.write_mode,
    disconnectSetting: ticketData.details.sync_disconnect_setting,
    remark: ticketData.remark,
  });
}
