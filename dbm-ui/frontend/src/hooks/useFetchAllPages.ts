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

import { useRequest } from 'vue-request';

// 调用方未指定 limit 时的分片条数，不超过后端单次上限
const DEFAULT_PAGE_SIZE = 10000;

/**
 * 分页接口取全量
 * 以响应里的 has_data 标记是否还有下一页；首片用初始参数请求，后续直接请求响应里的 next 地址
 */
export const useFetchAllPages = <P extends { limit?: number }, T>(
  request: (params: P, next: string) => Promise<{ has_data: boolean; next: string; results: T[] }>,
) => {
  // 用 shallowRef 避免泛型数组被深解包导致类型失真
  const data = shallowRef([] as T[]);

  const { loading, run, runAsync } = useRequest(
    async (params: P) => {
      const list: T[] = [];
      // 首片 next 为空，后续直接请求上一片返回的 next 地址
      let next = '';
      let hasMore = true;

      while (hasMore) {
        const page = await request({ ...params, limit: params.limit ?? DEFAULT_PAGE_SIZE }, next);
        const chunk = page.results;
        // 是否还有下一页只看 has_data，在写入本片数据之前先判定
        hasMore = page.has_data === true;
        // 分片为空兜底，避免异常时无限续拉
        if (chunk.length === 0) {
          break;
        }

        // 最后一片（has_data 为 false）的数据也要保留
        list.push(...chunk);

        // 没有下一页地址时结束（本片数据已保留）
        if (!page.next) {
          break;
        }
        next = page.next;
      }

      return list;
    },
    {
      manual: true,
      onSuccess(result) {
        data.value = result;
      },
    },
  );

  return {
    data,
    loading,
    run,
    runAsync,
  };
};
