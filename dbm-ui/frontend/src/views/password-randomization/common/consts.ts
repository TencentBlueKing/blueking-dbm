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

import { t }  from '@locales/index';

export const TYPE_OPTIONS = [
  {
    value: 'day',
    label: t('每天'),
  },
  {
    value: 'week',
    label: t('每周'),
  },
  {
    value: 'month',
    label: t('每月'),
  },
];

export const WEEK_OPTIONS = [
  {
    value: 'monday',
    label: t('周一'),
  },
  {
    value: 'tuesday',
    label: t('周二'),
  },
  {
    value: 'wendesday',
    label: t('周三'),
  },
  {
    value: 'thursday',
    label: t('周四'),
  },
  {
    value: 'friday',
    label: t('周五'),
  },
  {
    value: 'saturday',
    label: t('周六'),
  },
  {
    value: 'sundy',
    label: t('周日'),
  },
];

export const POLICY_MAP: {
  contains: Record<string, string>
  follows: Record<string, string>
} = {
  contains: {
    uppercase: t('大写字母'),
    lowercase: t('小写字母'),
    numbers: t('数字'),
    symbols: t('特殊字符_除空格外'),
  },
  follows: {
    keyboards: t('键盘序'),
    letters: t('字母序'),
    numbers: t('数字序'),
    repeats: t('连续特殊符号序'),
    symbols: t('重复字母_数字_特殊符号'),
  },
};
