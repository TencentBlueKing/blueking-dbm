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

import { match } from 'pinyin-pro';

/**
 * 判断 label 是否命中关键字（不做分隔符拆分），支持原文、拼音全拼与首字母匹配，多音字的各读音都参与匹配
 * @example isLabelMatch('重建中', 'cjz') // true
 */
export const isLabelMatch = (label: string, keyword: string) => {
  const target = `${keyword ?? ''}`.trim().toLowerCase();
  if (!target) {
    return true;
  }

  const source = `${label ?? ''}`;
  if (source.toLowerCase().includes(target)) {
    return true;
  }

  // 拼音匹配：每个字可按全拼或拼音前缀连续命中
  return Boolean(match(source, target, { continuous: true, precision: 'start' }));
};
