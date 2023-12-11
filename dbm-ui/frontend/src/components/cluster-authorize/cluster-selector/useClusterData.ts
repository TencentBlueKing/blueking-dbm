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

import _ from 'lodash';

import { getModules } from '@services/source/cmdb';
import { getResources as getSpiderResources } from '@services/source/spider';
import { getTendbhaList } from '@services/source/tendbha';
import { getTendbsingleList } from '@services/source/tendbsingle';

import { useGlobalBizs } from '@stores';

import {
  ClusterTypes,
  DBTypes,
} from '@common/const';

import { getSearchSelectorParams } from '@utils';

import type { ClusterSelectorState } from './types';

type ResourceItem = ServiceReturnType<typeof getTendbhaList>['results'][number]

/**
 * 处理集群列表数据
 */
export function useClusterData(state: ClusterSelectorState) {
  const globalBizsStore = useGlobalBizs();

  const apiMap: Record<string, (params: any) => ReturnType<typeof getTendbsingleList>> = {
    [ClusterTypes.TENDBSINGLE]: getTendbsingleList,
    [ClusterTypes.TENDBHA]: getTendbhaList,
    [ClusterTypes.TENDBCLUSTER]: getSpiderResources,
  };

  /**
   * 获取集群列表请求参数
   */
  function getResourcesParams() {
    return {
      dbType: DBTypes.MYSQL,
      type: state.activeTab === ClusterTypes.TENDBCLUSTER ? 'spider' : state.activeTab,
      bk_biz_id: globalBizsStore.currentBizId,
      ...state.pagination.getFetchParams(),
      ...getSearchSelectorParams(state.search),
    };
  }

  /**
   * 获取列表
   */
  const fetchResources = () => {
    state.isLoading = true;
    return apiMap[state.activeTab](getResourcesParams())
      .then((res) => {
        state.pagination.count = res.count;
        if (([ClusterTypes.TENDBHA, ClusterTypes.TENDBCLUSTER] as string[]).includes(state.activeTab)) {
          const list: ResourceItem[] = [];
          res.results.forEach((item) => {
            Object.assign(item, {
              isMaster: true,
            });
            list.push(item);
            if (item.slave_domain) {
              const slaveItem = _.cloneDeep(item);
              slaveItem.master_domain = item.slave_domain;
              slaveItem.isMaster = false;
              list.push(slaveItem);
            }
          });
          state.tableData = list;
        } else {
          state.tableData = res.results;
        }
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

  /**
   * 获取模块列表
   */
  const fetchModules = () => {
    getModules({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: state.activeTab,
    }).then((res) => {
      state.dbModuleList = res.map(item => ({
        id: item.db_module_id,
        name: item.name,
      }));
      return state.dbModuleList;
    });
  };

  return {
    fetchResources,
    fetchModules,
    handleChangePage,
    handeChangeLimit,
  };
}
