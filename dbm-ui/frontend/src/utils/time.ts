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
export function getDiffDyas(start: string, end: string) {
  const startTime = dayjs(start).toDate();
  const endTime = dayjs(end).toDate();
  const dateArr = [];
  while ((endTime.getTime() - startTime.getTime()) >= 0) {
    const year = startTime.getFullYear();
    const month = startTime.getMonth().toString().length === 1
      ? (parseInt(startTime.getMonth().toString(), 10) + 1) : (startTime.getMonth() + 1);
    const day = startTime.getDate().toString().length === 1 ? `0${startTime.getDate()}` : startTime.getDate();
    dateArr.push(`${year}-${month}-${day}`);
    startTime.setDate(startTime.getDate() + 1);
  }
  return dateArr;
}
