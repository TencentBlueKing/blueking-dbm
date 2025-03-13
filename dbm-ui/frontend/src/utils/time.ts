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
export function utcDisplayTime(time?: string) {
  if (!time) {
    return '';
  }
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss ZZ');
}

// 带时区时间字符串转秒级时间戳
export function utcTimeToSeconds(time?: string) {
  if (!time) {
    return 0;
  }
  return Math.floor(dayjs(time).valueOf() / 1000);
}

/**
 * 判断 YYYY-MM-DD HH:MM:SS 格式的时间是否合法
 * @param datetimeStr
 * @returns
 */
export function isValidDateTime(datetimeStr: string) {
  const isLeapYear = (year: number) => (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;

  const datetimeRegex = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/;
  const match = datetimeStr.match(datetimeRegex);

  if (!match) {
    return false;
  }

  const year = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const day = parseInt(match[3], 10);
  const hour = parseInt(match[4], 10);
  const minute = parseInt(match[5], 10);
  const second = parseInt(match[6], 10);

  if (
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > 31 ||
    hour < 0 ||
    hour > 23 ||
    minute < 0 ||
    minute > 59 ||
    second < 0 ||
    second > 59
  ) {
    return false;
  }

  const monthDays = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (day > monthDays[month - 1]) {
    return false;
  }

  return true;
}
