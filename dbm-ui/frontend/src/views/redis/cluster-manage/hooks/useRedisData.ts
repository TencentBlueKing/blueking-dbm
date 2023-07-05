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

import { getResources } from '@services/clusters';
import type { ResourceRedisItem } from '@services/types/clusters';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';

import { getSearchSelectorParams } from '@utils';

import type { RedisState } from '../../common/types';

/**
 * 处理 redis 列表数据
 */
export const useRedisData = (state: RedisState) => {
  const globalBizsStore = useGlobalBizs();

  /**
   * 获取列表
   */
  function fetchResources(extraParams = {}, isLoading = true) {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      type: DBTypes.REDIS,
      ...state.pagination.getFetchParams(),
      ...getSearchSelectorParams(state.searchValues),
      ...extraParams,
    };

    state.isInit = false;
    state.isLoading = isLoading;
    return getResources<ResourceRedisItem>(DBTypes.REDIS, params)
      .then((res) => {
        console.log('getResources>>', res);
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
  }

  /**
   * change page
   */
  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchResources();
  }

  /**
   * change limit
   */
  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  /**
   * change filter search values
   */
  const handleFilter = () => {
    nextTick(() => {
      handleChangePage(1);
    });
  };

  return {
    state,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
    handleFilter,
  };
};
