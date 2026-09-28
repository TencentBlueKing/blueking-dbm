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

/**
 * 分页接口取全量
 * 以响应里的 has_data 标记是否还有下一页，从 offset 0 逐片串行续拉，无下一页时结束
 */
export const useFetchAllPages = <P extends { limit?: number; offset?: number }, T>(
  request: (params: P) => Promise<{ has_data: boolean; results: T[] }>,
) => {
  // 用 shallowRef 避免泛型数组被深解包导致类型失真
  const data = shallowRef([] as T[]);

  const { loading, run, runAsync } = useRequest(
    async (params: P) => {
      const list: T[] = [];
      let offset = params.offset ?? 0;
      let isFinished = false;

      while (!isFinished) {
        const page = await request({
          ...params,
          offset,
        });
        const chunk = page.results;
        // 是否还有下一页只看 has_data，在写入本片数据之前先判定
        isFinished = page.has_data !== true;

        if (chunk.length > 0) {
          list.push(...chunk);
          offset += chunk.length;
        }
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
