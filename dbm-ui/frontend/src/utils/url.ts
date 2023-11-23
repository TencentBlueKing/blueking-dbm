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

export const parseURL = (url: string) => {
  const a = document.createElement('a');
  a.href = url;

  return {
    source: url,
    protocol: a.protocol.replace(':', ''),
    host: a.hostname,
    pathname: a.pathname.replace(/\/?$/, '/'),
    port: a.port,
    search: a.search.replace(/^\?/, ''),
    hash: a.hash.replace('#', ''),
    origin: a.origin,
  };
};

export const buildURLParams = (params: any) => {
  function forEach(obj:any, fn:any) {
    // Don't bother if no value provided
    if (obj === null || typeof obj === 'undefined') {
      return;
    }

    // Force an array if not already something iterable
    if (typeof obj !== 'object') {
      /* eslint no-param-reassign:0*/
      obj = [obj];
    }

    if (_.isArray(obj)) {
      // Iterate over array values
      for (let i = 0, l = obj.length; i < l; i++) {
        fn(obj[i], i, obj);
      }
    } else {
      // Iterate over object keys
      Object.keys(obj).forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          fn(obj[key], key, obj);
        }
      });
    }
  }
  function encode(val:string) {
    return encodeURIComponent(val)
      .replace(/%40/gi, '@')
      .replace(/%3A/gi, ':')
      .replace(/%24/g, '$')
      .replace(/%2C/gi, ',')
      .replace(/%20/g, '+')
      .replace(/%5B/gi, '[')
      .replace(/%5D/gi, ']');
  }
  /* eslint no-param-reassign:0*/
  if (!params) {
    return '';
  }

  const parts: Array<string> = [];

  forEach(params, (val:any, key: any) => {
    if (val === null || typeof val === 'undefined') {
      return;
    }

    if (_.isArray(val)) {
      key = `${key}[]`;
    } else {
      val = [val];
    }

    forEach(val, (v:any) => {
      if (_.isDate(v)) {
        v = v.toISOString();
      } else if (_.isObject(v)) {
        v = JSON.stringify(v);
      }
      parts.push(`${encode(key)}=${encode(v)}`);
    });
  });
  return parts.join('&');
};

