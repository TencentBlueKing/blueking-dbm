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

import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
import { getTendbclusterListByBizId } from '@services/source/tendbcluster';
import { getTendbhaListByBizId } from '@services/source/tendbha';
import { getTendbsingleListByBizId } from '@services/source/tendbsingle';

import { useDefaultPagination } from '@hooks';

import { ClusterTypes, DBTypes } from '@common/const';

import { getSearchSelectorParams } from '@utils';

export function useTargetClusterData(ticketDetails: TicketModel<Mysql.AuthorizeRules>) {
  const { t } = useI18n();
  const apiMap = {
    [ClusterTypes.TENDBCLUSTER]: getTendbclusterListByBizId,
    [ClusterTypes.TENDBHA]: getTendbhaListByBizId,
    [ClusterTypes.TENDBSINGLE]: getTendbsingleListByBizId,
  };

  const listState = reactive({
    data: [] as {
      cluster_name: string;
      db_module_name: string;
      master_domain: string;
      status: string;
    }[],
    dbModuleList: [] as {
      id: number | string;
      name: string;
    }[],
    filters: {
      search: [] as ISearchValue[],
    },
    isAnomalies: false,
    isLoading: false,
    pagination: useDefaultPagination(),
  });

  /**
   * search select 过滤参数
   */
  const searchSelectData = computed(() => [
    {
      id: 'domain',
      name: t('域名'),
    },
    {
      id: 'cluster_name',
      name: t('集群'),
    },
    {
      children: listState.dbModuleList,
      id: 'db_module_id',
      name: t('所属DB模块'),
    },
  ]);

  /**
   * 获取目标集群列表
   */
  const fetchCluster = () => {
    const type = ticketDetails?.details?.authorize_data?.cluster_type as keyof typeof apiMap;

    if (!apiMap[type]) {
      return;
    }

    const params = {
      bk_biz_id: ticketDetails.bk_biz_id,
      cluster_ids: ticketDetails.details.authorize_data?.cluster_ids,
      dbType: DBTypes.MYSQL,
      type,
      ...listState.pagination.getFetchParams(),
      ...getSearchSelectorParams(listState.filters.search),
    };
    listState.isLoading = true;

    apiMap[type](params)
      .then((res) => {
        listState.pagination.count = res.count;
        listState.data = res.results;
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
    fetchCluster,
    handeChangeLimit,
    handleChangePage,
    handleChangeValues,
    listState,
    searchSelectData,
  };
}
