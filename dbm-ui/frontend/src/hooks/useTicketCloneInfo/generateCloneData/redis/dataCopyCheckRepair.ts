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
import dayjs from 'dayjs';

import type { RedisDataCheckAndRepairDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

import { t } from '@locales/index';

// Redis 数据校验与修复
export function generateRedisDataCopyCheckRepairCloneData(ticketData: TicketModel<RedisDataCheckAndRepairDetails>) {
  const { details } = ticketData;
  const tableList = details.infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    billId: item.bill_id,
    srcCluster: item.src_cluster,
    targetCluster: item.dst_cluster,
    relateTicket: item.bill_id,
    instances: t('全部'),
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
  }));

  return Promise.resolve({
    tableList,
    executeType: details.execute_mode,
    executeTime: dayjs(details.specified_execution_time).toDate(),
    stopTime: dayjs(details.check_stop_time).toDate(),
    isKeepCheck: details.keep_check_and_repair,
    isRepairEnable: details.data_repair_enabled,
    repairType: details.repair_mode,
    remark: ticketData.remark,
  });
}
