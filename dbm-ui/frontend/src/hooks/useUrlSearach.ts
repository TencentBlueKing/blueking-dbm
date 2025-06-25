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

import { buildURLParams } from '@utils';

export const useUrlSearch = () => {
  const searchParams = new URLSearchParams(window.location.search);

  const getSearchParams = () => {
    const curSearchParams = new URLSearchParams(window.location.search);
    return Array.from(curSearchParams.keys()).reduce(
      (result, key) => ({
        ...result,
        [key]: curSearchParams.get(key) || '',
      }),
      {} as Record<string, string>,
    );
  };

  const appendSearchParams = (params: Record<string, any>, localtion = true) => {
    const curSearchParams = new URLSearchParams(window.location.search);
    Object.keys(params).forEach((key) => {
      if (curSearchParams.has(key)) {
        curSearchParams.set(key, params[key]);
      } else {
        curSearchParams.append(key, params[key]);
      }
    });
    if (localtion) {
      window.history.replaceState({}, '', `?${curSearchParams.toString()}`);
    }
    return Array.from(curSearchParams.keys()).reduce(
      (result, key) => ({
        ...result,
        [key]: curSearchParams.get(key) || '',
      }),
      {} as Record<string, string>,
    );
  };

  const removeSearchParam = (paramKey: string | Array<string>, localtion = true) => {
    const keyList = Array.isArray(paramKey) ? paramKey : [paramKey];
    const curSearchParams = new URLSearchParams(window.location.search);
    keyList.forEach((key) => {
      curSearchParams.delete(key);
    });
    if (localtion) {
      window.history.replaceState({}, '', `?${curSearchParams.toString()}`);
    }
    return Array.from(curSearchParams.keys()).reduce(
      (result, key) => ({
        ...result,
        [key]: curSearchParams.get(key) || '',
      }),
      {} as Record<string, string>,
    );
  };

  const replaceSearchParams = (params: Record<string, any>, localtion = true) => {
    const privateParams = getSearchParams();

    // 全部替换时忽略 __ 开头的并且是__结尾的 key, 此类可以作为页面状态存储用
    Object.keys(privateParams).forEach((key) => {
      if (/^__(.+)__$/.test(key)) {
        return;
      }
      delete privateParams[key];
    });

    const latestParams = Object.assign({}, params, privateParams);

    if (localtion) {
      window.history.replaceState({}, '', `?${buildURLParams(latestParams)}`);
    }
    return latestParams;
  };

  return {
    appendSearchParams,
    getSearchParams,
    removeSearchParam,
    replaceSearchParams,
    searchParams,
  };
};
