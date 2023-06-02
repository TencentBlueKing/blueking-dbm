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

import { getResourceInstances } from '@services/clusters';
import type { ResourceInstance } from '@services/types/clusters';

import { useDefaultPagination } from '@hooks';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';

import { getSearchSelectorParams } from '@utils';

type Props = {
  clusterType: string
};

/**
 * 处理实例列表数据
 */
export const useInstanceData = (props: Props) => {
  const globalBizsStore = useGlobalBizs();

  const state = reactive({
    loading: false,
    data: [] as ResourceInstance[],
    pagination: useDefaultPagination(),
    filters: {
      search: [] as ISearchValue[],
    },
  });

  // 获取实例列表参数
  const fetchParams = computed(() => ({
    bk_biz_id: globalBizsStore.currentBizId,
    type: props.clusterType,
    ...state.pagination.getFetchParams(),
    ...getSearchSelectorParams(state.filters.search),
  }));

  /**
    * 获取实例列表
    */
  function fetchResourceInstances(address?: string) {
    state.loading = true;
    const params = { ...fetchParams.value, db_type: DBTypes.MYSQL };
    if (address) {
      Object.assign(params, { instance_address: address });
    }
    return getResourceInstances(params)
      .then((res) => {
        state.pagination.count = res.count;
        state.data = res.results;
        return res;
      })
      .finally(() => {
        state.loading = false;
      });
  }

  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchResourceInstances();
  }

  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  return {
    state,
    fetchResourceInstances,
    handleChangePage,
    handeChangeLimit,
  };
};
