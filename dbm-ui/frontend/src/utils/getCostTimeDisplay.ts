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

import { intervalToDuration } from 'date-fns';

const times = [{
  key: 'years',
  unit: 'y',
}, {
  key: 'months',
  unit: 'M',
}, {
  key: 'days',
  unit: 'd',
}, {
  key: 'hours',
  unit: 'h',
}, {
  key: 'minutes',
  unit: 'm',
}, {
  key: 'seconds',
  unit: 's',
}];
/**
 * 获取耗时展示文本
 * @param time timestamp 秒级
 * @returns cost time display
 */
export const getCostTimeDisplay = (time: number) => {
  if (!time) return time === 0 ? '0s' : '--';

  const duration: { [key: string]: number } = intervalToDuration({
    start: 0,
    end: time * 1000,
  });
  let timeDisplay = '';
  for (const { key, unit } of times) {
    const value = duration[key];
    if (value || timeDisplay) {
      timeDisplay += `${value}${unit}`;
    }
  }
  return timeDisplay;
};
