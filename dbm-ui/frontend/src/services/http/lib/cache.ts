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

export type CacheValue = Promise<any>;
export type CacheExpire = number | boolean;

export interface ICache {
  set: (name: string, value: CacheValue, expire: CacheExpire) => boolean;
  get: (name: string) => any;
  has: (name: string) => boolean;
  delete: (name: string) => boolean;
  clear: () => boolean;
}

export default class Cache implements ICache {
  cacheMap: Map<string, CacheValue>;
  cacheExpireMap: Map<string, number>;
  constructor() {
    this.cacheMap = new Map();
    this.cacheExpireMap = new Map();
  }
  set(name: string, value: CacheValue, expire: CacheExpire) {
    if (_.isNumber(expire)) {
      this.cacheExpireMap.set(name, Date.now() + expire);
    }
    if (!this.cacheMap.has(name)) {
      this.cacheMap.set(name, value);
    }
    return true;
  }
  get(name: string) {
    if (this.cacheMap.has(name)) {
      return this.cacheMap.get(name);
    }
    return false;
  }
  has(name: string) {
    if (!this.cacheMap.has(name)) {
      return false;
    }
    const expire = this.cacheExpireMap.get(name);
    if (!expire) {
      return true;
    }
    if (Date.now() > expire) {
      this.cacheMap.delete(name);
      this.cacheExpireMap.delete(name);
      return false;
    }
    return true;
  }
  delete(name: string) {
    if (this.cacheMap.has(name)) {
      return this.cacheMap.delete(name);
    }
    return true;
  }
  clear() {
    this.cacheMap.clear();
    return this.cacheMap.size < 1;
  }
}
