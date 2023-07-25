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

import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';

import type { ResourceRedisItem } from '@services/types/clusters';

import type { IPagination } from '@hooks';

/**
 * redis 集群列表基础数据类型
 */
export interface RedisState {
  isInit: boolean,
  isAnomalies: boolean,
  isLoading: boolean,
  data: ResourceRedisItem[],
  selected: ResourceRedisItem[],
  searchValues: ISearchValue[],
  pagination: IPagination,
}


export enum AffinityType {
  SAME_SUBZONE_CROSS_SWTICH = 'SAME_SUBZONE_CROSS_SWTICH', // 同城同subzone跨交换机跨机架
  SAME_SUBZONE = 'SAME_SUBZONE', // 同城同subzone
  CROS_SUBZONE = 'CROS_SUBZONE', // 同城跨subzone
  NONE = 'NONE', // 无需亲和性处理
}


export enum RepairAndVerifyFrequencyModes {
  ONCE_AFTER_REPLICATION = 'once_after_replication', // 复制完成后，只进行一次
  ONCE_EVERY_THREE_DAYS = 'once_every_three_days', // 复制完成后，每三天一次
  ONCE_WEEKLY = 'once_weekly', // 复制完成后，每周一次
}

export enum WriteModes {
  DELETE_AND_WRITE_TO_REDIS = 'delete_and_write_to_redis', // 先删除同名redis key, 在执行写入 (如: del $key + hset $key)
  KEEP_AND_APPEND_TO_REDIS = 'keep_and_append_to_redis', // 保留同名redis key,追加写入
  FLUSHALL_AND_WRITE_TO_REDIS = 'flushall_and_write_to_redis', // 先清空目标集群所有数据,在写入
}

export enum DisconnectModes {
  AUTO_DISCONNECT_AFTER_REPLICATION = 'auto_disconnect_after_replication', // 复制完成后，自动断开
  KEEP_SYNC_WITH_REMINDER = 'keep_sync_with_reminder', // 不断开，定时发送断开提醒
}

export enum RemindFrequencyModes {
  ONCE_DAILY = 'once_daily', // 一天一次
  ONCE_WEEKLY = 'once_weekly', // 一周一次
}

export enum RepairAndVerifyModes {
  DATA_CHECK_AND_REPAIR = 'data_check_and_repair', // 数据校验并修复
  DATA_CHECK_ONLY = 'data_check_only', // 仅进行数据校验，不进行修复
  NO_CHECK_NO_REPAIR = 'no_check_no_repair', // 不校验不修复
}

export enum CopyModes {
  INTRA_BISNESS = 'one_app_diff_cluster', // 业务内
  CROSS_BISNESS = 'diff_app_diff_cluster', // 跨业务
  INTRA_TO_THIRD = 'copy_to_other_system', // 业务内至第三方
  SELFBUILT_TO_INTRA = 'user_built_to_dbm', // 自建集群至业务内
}
