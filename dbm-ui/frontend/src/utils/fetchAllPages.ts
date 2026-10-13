/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

/**
 * 游标分页取全量
 * 首片不传游标（返回的是日志尾部最新的分片），之后把响应里的 search_after 原样带回，直到 has_data 为 false
 * 调用方未指定 limit 时取默认值，并保证后续每一片请求都带上同一初始 limit
 * 抓取顺序为「新 → 旧」，最终按页逆序拼接，返回整体按时间升序（旧 → 新）的全量数据
 * 分片为空兜底终止，避免游标异常时无限续拉
 */
// 调用方未指定 limit 时的分片条数，不超过后端单次上限
const DEFAULT_PAGE_SIZE = 10000;

export async function fetchAllPages<
  P extends {
    limit?: number;
    search_after?: (number | string)[];
  },
  T,
>(
  request: (params: P) => Promise<{
    has_data: boolean;
    results: T[];
    search_after: (number | string)[];
  }>,
  params: P,
) {
  const pages: T[][] = [];
  // 归一化后的初始 limit，后续每一片请求都原样带上
  const baseParams = { ...params, limit: params.limit ?? DEFAULT_PAGE_SIZE };
  let searchAfter: (number | string)[] | undefined = params.search_after;
  let hasMore = true;

  while (hasMore) {
    const page = await request({
      ...baseParams,
      search_after: searchAfter,
    });
    pages.push(page.results);
    hasMore = page.has_data === true && page.results.length > 0;
    searchAfter = page.search_after;
  }

  return pages.reverse().flat();
}
