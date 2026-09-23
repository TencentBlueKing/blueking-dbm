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

export interface Pagination {
  align: string;
  count: number;
  current: number;
  layout: Array<'total' | 'list' | 'limit'>;
  limit: number;
  limitList: Array<number>;
}

export const usePagination = (options?: { callback: () => void; defaultLimit?: number }) => {
  const defaultLimit = options?.defaultLimit ?? 20;
  const pagination = reactive<Pagination>({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: defaultLimit,
    limitList: [10, 20, 50, 100, 200, 500],
  });

  const onChange = (pageValue: number) => {
    if (pagination.current === pageValue) {
      return;
    }
    pagination.current = pageValue;
    options?.callback();
  };

  const onLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit) {
      return;
    }
    pagination.limit = pageLimit;
    pagination.current = 1;
    options?.callback();
  };

  return {
    onChange,
    onLimitChange,
    pagination,
  };
};
