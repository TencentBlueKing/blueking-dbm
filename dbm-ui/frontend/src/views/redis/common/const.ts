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
import { CopyModes, DisconnectModes, RemindFrequencyModes, RepairAndVerifyFrequencyModes, RepairAndVerifyModes, WriteModes } from '@services/model/redis/redis-dst-history-job';

export const repairAndVerifyFrequencyList = [
  {
    value: RepairAndVerifyFrequencyModes.ONCE_AFTER_REPLICATION,
    label: '复制完成后，只进行一次',
  },
  {
    value: RepairAndVerifyFrequencyModes.ONCE_EVERY_THREE_DAYS,
    label: '复制完成后，每三天一次',
  },
  {
    value: RepairAndVerifyFrequencyModes.ONCE_WEEKLY,
    label: '复制完成后，每周一次',
  },
];

export const writeTypeList = [
  {
    label: '先删除同名 Key，再写入（如：del  $key+ hset $key）',
    value: WriteModes.DELETE_AND_WRITE_TO_REDIS,
  },
  {
    label: '保留同名 Key，追加写入（如：hset $key）',
    value: WriteModes.KEEP_AND_APPEND_TO_REDIS,
  },
  {
    label: '清空目标集群所有数据，再写入',
    value: WriteModes.FLUSHALL_AND_WRITE_TO_REDIS,
  },
];

export const copyTypeList = [
  {
    label: '业务内',
    value: CopyModes.INTRA_BISNESS,
  },
  {
    label: '跨业务',
    value: CopyModes.CROSS_BISNESS,
  },
  {
    label: '业务内至第三方',
    value: CopyModes.INTRA_TO_THIRD,
  },
  {
    label: '自建集群至业务内',
    value: CopyModes.SELFBUILT_TO_INTRA,
  },
];

export const disconnectTypeList = [
  {
    label: '复制完成后，自动断开',
    value: DisconnectModes.AUTO_DISCONNECT_AFTER_REPLICATION,
  },
  {
    label: '不断开，定时发送断开提醒',
    value: DisconnectModes.KEEP_SYNC_WITH_REMINDER,
  },
];

export const remindFrequencyTypeList = [
  {
    label: '一天一次（早上 10:00）',
    value: RemindFrequencyModes.ONCE_DAILY,
  },
  {
    label: '一周一次（早上 10:00）',
    value: RemindFrequencyModes.ONCE_WEEKLY,
  },
];

export const repairAndVerifyTypeList = [
  {
    label: '校验并修复',
    value: RepairAndVerifyModes.DATA_CHECK_AND_REPAIR,
  },
  {
    label: '只校验，不修复',
    value: RepairAndVerifyModes.DATA_CHECK_ONLY,
  },
  {
    label: '不校验，不修复',
    value: RepairAndVerifyModes.NO_CHECK_NO_REPAIR,
  },
];
