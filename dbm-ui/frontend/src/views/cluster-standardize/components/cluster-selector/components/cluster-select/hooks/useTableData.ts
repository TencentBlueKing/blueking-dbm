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

import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';

import type TendbhaModel from '@services/model/mysql/tendbha';
import { getClusterList as getTableList } from '@services/source/mysql';

import { getSearchSelectorParams } from '@utils';

/**
 * 处理集群列表数据
 */
export function useTableData(
  searchSelectValue: Ref<ISearchValue[]>,
  params: ComputedRef<{ bk_biz_id?: number; db_module_id?: number }>,
) {
  const isLoading = ref(false);
  const tableData = shallowRef<TendbhaModel[]>([]);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });

  watch(searchSelectValue, () => {
    setTimeout(() => {
      handleChangePage(1);
    });
  });

  const fetchResources = async () => {
    isLoading.value = true;
    const definedParams = {
      limit: pagination.limit,
      offset: (pagination.current - 1) * pagination.limit,
      extra: 1,
      ...getSearchSelectorParams(searchSelectValue.value),
    };
    return getTableList(Object.assign(definedParams, params.value))
      .then((data) => {
        const ret = data;
        tableData.value = ret.results;
        pagination.count = ret.count;
      })
      .catch(() => {
        tableData.value = [];
        pagination.count = 0;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const handleChangePage = (value: number) => {
    pagination.current = value;
    return fetchResources();
  };

  const handeChangeLimit = (value: number) => {
    pagination.limit = value;
    return handleChangePage(1);
  };

  return {
    isLoading,
    data: tableData,
    pagination,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  };
}
