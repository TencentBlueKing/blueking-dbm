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

import _ from 'lodash';

export const listColumnsCache = {
  key: 'list_column_display',
  setItem(key: string, value: { columns: Array<string>; size: string }) {
    const lastValue = listColumnsCache.getItem() || {};
    localStorage.setItem(
      listColumnsCache.key,
      JSON.stringify({
        ...lastValue,
        [key]: value,
      }),
    );
  },
  getItem(key?: string) {
    try {
      const allCache = JSON.parse(localStorage.getItem(listColumnsCache.key) || '');
      if (!_.isPlainObject(allCache)) {
        return false;
      }
      if (!key) {
        return allCache;
      }
      if (!allCache[key]) {
        return false;
      }
      if (!allCache[key].columns || !allCache[key].size) {
        return false;
      }
      return allCache[key];
    } catch {
      return false;
    }
  },
  clearItem() {
    localStorage.removeItem(listColumnsCache.key);
  },
};
