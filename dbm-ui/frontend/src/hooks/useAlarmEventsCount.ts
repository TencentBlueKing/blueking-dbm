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

import { getAlarmEventsList } from '@services/source/monitor';

import { useUserProfile } from '@stores';

/**
 * 告警事件统计数据
 */
export const useAlarmEventsCount = () => {
  const { isDba } = useUserProfile();

  const todoCount = ref(0);
  const assitCount = ref(0);

  const initCount = () => {
    const dateFormatStr = 'YYYY-MM-DD HH:mm:ss';
    const startTime = dayjs().subtract(7, 'day').format(dateFormatStr);
    const endTime = dayjs().format(dateFormatStr);
    Promise.all([
      getAlarmEventsList({
        end_time: endTime,
        self_manage: true,
        start_time: startTime,
        status: 'ABNORMAL',
      }),
      getAlarmEventsList({
        end_time: endTime,
        self_assist: true,
        start_time: startTime,
        status: 'ABNORMAL',
      }),
    ]).then(([todoData, assistData]) => {
      todoCount.value = todoData.overview.count ?? 0;
      assitCount.value = assistData.overview.count ?? 0;
    });
  };
  if (isDba) {
    initCount();
  }

  return {
    assitCount,
    todoCount,
  };
};
