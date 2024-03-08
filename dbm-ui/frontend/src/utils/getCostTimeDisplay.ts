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

/**
 * 获取耗时展示文本
 * @param time timestamp 秒级
 * @returns cost time display
 */
export const getCostTimeDisplay = (time: number) => {
  const totalTime = time;
  if (totalTime < 60) {
    return `${totalTime}s`;
  }
  const dayUnit = 86400;
  const hourUnit = 3600;
  const minUnit = 60;
  const stack = [];
  const day = Math.floor(time / dayUnit);
  if (day) {
    stack.push(`${day}d`);
  }
  const hour = Math.floor((time % dayUnit) / hourUnit);
  if (hour) {
    stack.push(`${hour}h`);
  }
  const min = Math.floor((time % hourUnit) / minUnit);
  if (min) {
    stack.push(`${min}m`);
  }
  const second = Math.ceil(time % 60);
  stack.push(`${second}s`);
  return stack.join(' ');
};
