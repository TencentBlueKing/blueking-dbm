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
import type { RedisRollbackDataCopyDetails } from '@services/model/ticket/details/redis';

import { random } from '@utils';

// Redis 以构造实例恢复
export function generateRedisRollbackDataCloneData(details: RedisRollbackDataCopyDetails) {
  const { clusters, infos } = details;
  const tableList = infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: item.src_cluster,
    targetTime: item.recovery_time_point,
    targetCluster: clusters[item.dst_cluster].immute_domain,
    targetClusterId: item.dst_cluster,
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
  }));

  return Promise.resolve({
    tableList,
    writeMode: details.write_mode,
  });
}
