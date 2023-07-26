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

import type { PermissionTableRow } from './types';

// 判断是否为新账号规则
export function isNewUser(row: PermissionTableRow) {
  const createTime = row.account.create_time;
  if (!createTime) return '';

  const createDay = new Date(createTime);
  const today = new Date();
  return differenceInHours(today, createDay) <= 24;
}

/**
   * 展开/收起渲染列表
   */
export function getRenderList(data: PermissionTableRow) {
  return data.isExpand ? data.rules : data.rules.slice(0, 1);
}
