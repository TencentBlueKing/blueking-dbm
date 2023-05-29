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

import { differenceInHours } from 'date-fns';

/**
 * 通过传入时间 yyyy-MM-dd HH:mm:ss | Date 判断是否为最近几天
 * @param date 时间
 * @param hours 用于判断是否为最近几天的小时数
 */
export const isRecentDays = (date: string | Date, hours: number) => {
  try {
    const createDay = new Date(date);
    const today = new Date();
    return differenceInHours(today, createDay) < hours;
  } catch (e) {
    return false;
  }
};
