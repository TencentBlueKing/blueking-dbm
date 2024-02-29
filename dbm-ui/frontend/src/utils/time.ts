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

// 获取两个日期间的所有日期
export function getDiffDays(start: string, end: string) {
  let startTime = dayjs(start);
  const endTime = dayjs(end);
  const dateArr = [];
  while (endTime.isAfter(startTime) || endTime.isSame(startTime)) {
    const date = startTime.format('YYYY-MM-DD');
    dateArr.push(date);
    startTime = startTime.add(1, 'day');
  }
  return dateArr;
}

// 统一的带时区时间显示
export function utcDisplayTime(time: string) {
  if (!time) {
    return '';
  }
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss ZZ');
}
