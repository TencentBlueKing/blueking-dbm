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

// import { getResources } from '@services/clusters';
import { getModules } from '@services/common';
import { listClusterList } from '@services/redis/toolbox';

// import type { ResourceItem } from '@services/types/clusters';
import { useGlobalBizs } from '@stores';

// import { DBTypes } from '@common/const';
// import { getSearchSelectorParams } from '@utils';
import type { ClusterSelectorState } from './types';

/**
 * 处理集群列表数据
 */
export function useClusterData(state: ClusterSelectorState) {
  /**
   * 获取列表
   */
  const fetchResources = () => {
    state.isLoading = true;
    return listClusterList()
      .then((res) => {
        state.pagination.count = res.length;
        state.tableData = res;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.tableData = [];
        state.pagination.count = 0;
        state.isAnomalies = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  /**
   * change page
   */
  const handleChangePage = (value: number) => {
    state.pagination.current = value;
    return fetchResources();
  };

  /**
   * change limit
   */
  const handeChangeLimit = (value: number) => {
    state.pagination.limit = value;
    return handleChangePage(1);
  };

  return {
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  };
}
