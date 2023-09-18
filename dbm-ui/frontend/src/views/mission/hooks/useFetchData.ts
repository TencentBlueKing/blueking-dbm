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

import { format } from 'date-fns';

import { getTaskflow } from '@services/taskflow';

import { useGlobalBizs } from '@stores';

import { getSearchSelectorParams } from '@utils';

import type { ListState } from '../common/types';

/**
 * 操作任务列表数据
 */
export const useFetchData = (state: ListState) => {
  const globalBizsStore = useGlobalBizs();

  /**
   * 任务列表日期过滤参数
   */
  const filterDate = computed(() => {
    const daterange = state.filter.daterange.filter(item => item);
    if (daterange.length === 0) {
      return {};
    }

    const [gte, lte] = daterange;
    return {
      created_at__gte: format(new Date(gte as string), 'yyyy-MM-dd HH:mm:ss'),
      created_at__lte: format(new Date(lte as string), 'yyyy-MM-dd HH:mm:ss'),
    };
  });

  /**
   * 查询任务列表
   */
  const fetchTaskflow = (filter = {}) => {
    state.isLoading = true;
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      ...filterDate.value,
      ...state.pagination.getFetchParams(),
      ...getSearchSelectorParams(state.filter.searchValues),
      ...filter,
    };
    return getTaskflow(params)
      .then((res) => {
        state.pagination.count = res.count;
        state.data = res.results;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.pagination.count = 0;
        state.data = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  // 查询列表数据
  fetchTaskflow();

  /**
   * table change page
   * @param value current page
   */
  const handeChangePage = (value: number) => {
    state.pagination.current = value;
    fetchTaskflow();
  };

  /**
   * table change limit
   * @param value limit
   */
  const handeChangeLimit = (value: number) => {
    state.pagination.limit = value;
    handeChangePage(1);
  };

  return {
    state,
    fetchTaskflow,
    handeChangePage,
    handeChangeLimit,
  };
};
