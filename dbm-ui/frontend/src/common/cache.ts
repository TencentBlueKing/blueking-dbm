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

export const routerCache = {
  key: 'router_history',
  setItem(key: string, value: any) {
    const cacheMap = JSON.parse(localStorage.getItem(routerCache.key) || '{}');
    cacheMap[key] = value;
    localStorage.setItem(routerCache.key, JSON.stringify(cacheMap));
  },
  getItem(key: string) {
    const cache = localStorage.getItem(routerCache.key);
    if (cache === null) return '';

    const cacheMap = JSON.parse(cache);
    if (_.isPlainObject(cacheMap)) {
      return !key ? cacheMap : cacheMap[key];
    }

    return '';
  },
  clearItem(key: string) {
    if (!key) {
      return false;
    }

    const cache = localStorage.getItem(routerCache.key);
    if (!cache) {
      return false;
    }

    const cacheMap = JSON.parse(cache);
    if (!cacheMap[key]) {
      return true;
    }

    delete cacheMap[key];
    localStorage.setItem(routerCache.key, JSON.stringify(cacheMap));
    return true;
  },
};

export const systemSearchCache = {
  key: 'SYSTEM_SEARCH_HISTORY_KEY_WORD',
  setItem(value: string[]) {
    localStorage.setItem(systemSearchCache.key, JSON.stringify(value));
  },
  appendItem(value: string) {
    const histroyList = systemSearchCache.getItem();
    histroyList.unshift(value);
    systemSearchCache.setItem(histroyList.slice(0, 10));
  },
  getItem(): string[] {
    const value = JSON.parse(localStorage.getItem(systemSearchCache.key) || '[]');
    return _.isArray(value) ? _.uniq(value) : [];
  },
};
