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
import { useI18n } from 'vue-i18n';

import type { MysqlAuthorizationDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { getResourcesByBizId as getSpiderResources } from '@services/source/spider';
import { getTendbhaListByBizId } from '@services/source/tendbha';
import { getTendbsingleListByBizId } from '@services/source/tendbsingle';
import type { ResourceItem, SearchFilterItem } from '@services/types';

import { useDefaultPagination } from '@hooks';

import { ClusterTypes, DBTypes } from '@common/const';

import { getSearchSelectorParams } from '@utils';

export function useTargetClusterData(ticketDetails: TicketModel<MysqlAuthorizationDetails>) {
  const { t } = useI18n();
  const apiMap = {
    [ClusterTypes.TENDBSINGLE]: getTendbsingleListByBizId,
    [ClusterTypes.TENDBHA]: getTendbhaListByBizId,
    spider: getSpiderResources,
  };

  const listState = reactive({
    isAnomalies: false,
    isLoading: false,
    data: [] as ResourceItem[],
    pagination: useDefaultPagination(),
    filters: {
      search: [] as ISearchValue[],
    },
    dbModuleList: [] as SearchFilterItem[],
  });

  /**
   * search select 过滤参数
   */
  const searchSelectData = computed(() => [
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: t('集群'),
      id: 'cluster_name',
    },
    {
      name: t('所属DB模块'),
      id: 'db_module_id',
      children: listState.dbModuleList,
    },
  ]);

  /**
   * 获取目标集群列表
   */
  const fetchCluster = () => {
    const type = (
      ticketDetails?.details?.authorize_data?.cluster_type === ClusterTypes.TENDBCLUSTER
        ? 'spider'
        : ticketDetails?.details?.authorize_data?.cluster_type
    ) as keyof typeof apiMap;

    if (!apiMap[type]) {
      return;
    }

    const params = {
      dbType: DBTypes.MYSQL,
      bk_biz_id: ticketDetails.bk_biz_id,
      type,
      cluster_ids: ticketDetails.details.authorize_data?.cluster_ids,
      ...listState.pagination.getFetchParams(),
      ...getSearchSelectorParams(listState.filters.search),
    };
    listState.isLoading = true;

    apiMap[type](params)
      .then((res) => {
        listState.pagination.count = res.count;
        listState.data = res.results as ResourceItem[];
        listState.isAnomalies = false;
      })
      .catch(() => {
        listState.pagination.count = 0;
        listState.data = [];
        listState.isAnomalies = true;
      })
      .finally(() => {
        listState.isLoading = false;
      });
  };

  /**
   * change page
   */
  const handleChangePage = (value: number) => {
    listState.pagination.current = value;
    fetchCluster();
  };

  /**
   * change limit
   */
  const handeChangeLimit = (value: number) => {
    listState.pagination.limit = value;
    handleChangePage(1);
  };

  /**
   * change filter search values
   */
  const handleChangeValues = () => {
    nextTick(() => {
      handleChangePage(1);
    });
  };

  return {
    listState,
    searchSelectData,
    fetchCluster,
    handleChangePage,
    handeChangeLimit,
    handleChangeValues,
  };
}
