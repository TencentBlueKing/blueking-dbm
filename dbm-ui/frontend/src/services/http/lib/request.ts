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

import axios, {
  type CancelTokenSource,
} from 'axios';
import Cookie from 'js-cookie';
import _ from 'lodash';

import { setCancelTokenSource } from '../index';
import requestMiddleware from '../middleware/request';
import responseMiddleware from '../middleware/response';

import Cache, {
  type CacheExpire,
  type CacheValue,
} from './cache';
import { paramsSerializer } from './utils';

const cacheHandler = new Cache();

export type Method = 'get' | 'delete'| 'post' | 'put' | 'download'
export interface Config {
  url: string,
  method: Method,
  params?: Record<string, any>,
  payload?: {
    timeout?: number,
    cache?: string | number | boolean,
    onUploadProgress?: (params: CancelTokenSource) => void,
    permission?: 'page' | 'dialog' | 'catch'
  }
}

requestMiddleware(axios.interceptors.request);
responseMiddleware(axios.interceptors.response);

const { CancelToken } = axios;
const CRRF_TOKEN_KEY = 'dbm_csrftoken';

const csrfHashCode = (key:string) => {
  let hashCode = 5381;
  for (let i = 0; i < key.length; i++) {
    hashCode += (hashCode << 5) + key.charCodeAt(i);
  }
  return hashCode & 0x7fffffff;
};
const CSRFToken = Cookie.get(CRRF_TOKEN_KEY);

axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
if (CSRFToken !== undefined) {
  axios.defaults.headers.common['X-CSRFToken'] = csrfHashCode(CSRFToken);
} else {
  console.warn('Can not find csrftoken in document.cookie');
}
const defaultConfig = {
  timeout: 60000,
  headers: {},
  withCredentials: true,
  paramsSerializer,
  xsrfCookieName: 'bk-audit_csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
};

export default class Request {
  static supporMethods = [
    'get', 'post', 'delete', 'put',
  ];
  static willCachedMethods = [
    'get',
  ];
  static bodyDataMethods = [
    'post', 'put', 'delete',
  ];

  cache: Cache;
  config: Config;

  constructor(config = {} as Config) {
    this.cache = cacheHandler;
    this.config = config;
  }

  get taskKey() {
    return `${this.config.method}_${this.config.url}_${JSON.stringify(this.config.params)}`;
  }

  get isCachedable() {
    if (!Request.willCachedMethods.includes(this.config.method)) {
      return false;
    }
    if (!this.config.payload || !_.has(this.config.payload, 'cache')) {
      return false;
    }
    return true;
  }

  get axiosConfig() {
    const config: Record<string, any> = Object.assign({}, defaultConfig, {
      baseURL: window.PROJECT_ENV.VITE_AJAX_URL_PREFIX,
      url: this.config.url,
      method: this.config.method,
      data: {},
      params: {},
      payload: this.config.payload || {},
    });

    if (this.config.params) {
      if (Request.bodyDataMethods.includes(this.config.method)) {
        config.data = this.config.params;
      } else {
        config.params = this.config.params;
      }
    }

    if (this.config.payload) {
      const configPayload = this.config.payload;
      Object.keys(configPayload).forEach((configExtend) => {
        config[configExtend] = configPayload[configExtend as keyof Config['payload']];
      });
    }

    return config;
  }

  checkCache() {
    return this.isCachedable && this.cache.has(this.taskKey);
  }

  setCache(data: CacheValue) {
    this.isCachedable && this.cache.set(this.taskKey, data, this.config.payload?.cache as CacheExpire);
  }

  deleteCache() {
    this.cache.delete(this.taskKey);
  }

  run() {
    if (this.checkCache()) {
      return this.cache.get(this.taskKey);
    }

    const source = CancelToken.source();
    setCancelTokenSource(source);

    const requestHandler = axios({
      ...this.axiosConfig,
      cancelToken: source.token,
    }).then((data) => {
      this.setCache(requestHandler);
      return data.data;
    });
    this.setCache(requestHandler);
    return requestHandler;
  }
}
