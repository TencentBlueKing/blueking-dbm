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

import isDate from 'lodash/isDate';
import isEmpty from 'lodash/isEmpty';

export default {
  email: (value: string): boolean => /^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$/.test(value),
  max: (value: number, max: number): boolean => max >= value,
  // 数组值按元素个数计算长度，其他类型按字符串长度计算
  maxlength: (value: unknown, maxlength: number): boolean =>
    (Array.isArray(value) ? value.length : String(value ?? '').length) <= maxlength,
  min: (value: number, min: number): boolean => value >= min,
  pattern: (value: string, pattern: RegExp): boolean => {
    const result = pattern.test(value);
    pattern.lastIndex = 0; // eslint-disable-line no-param-reassign
    return result;
  },
  required: (value: any): boolean => {
    if (typeof value === 'number' || typeof value === 'boolean' || isDate(value)) {
      return true;
    }
    return !isEmpty(value);
  },
};
