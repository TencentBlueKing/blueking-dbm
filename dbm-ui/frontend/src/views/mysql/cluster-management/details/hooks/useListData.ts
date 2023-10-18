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

import { getResources, getTableFields } from '@services/clusters';
import { getModules } from '@services/common';
import type {
  ResourceItem,
  TableFieldsItem,
} from '@services/types/clusters';
import type { ModuleItem } from '@services/types/common';

import { useDefaultPagination } from '@hooks';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';

import type { Item } from '@components/vue2/search-select/index.vue';

import { getSearchSelectorParams } from '@utils';

type Props = {
  clusterType: string
};

type FetchParams = {
  domain?: string,
};

/**
 * 处理集群列表数据
 */
export function useListData(props: Props) {
  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const listState = reactive({
    isAnomalies: false,
    loading: false,
    fieldsLoading: false,
    pagination: useDefaultPagination(),
    fields: [] as TableFieldsItem[],
    data: [] as ResourceItem[],
    filters: {
      search: [] as ISearchValue[],
    },
    moduleList: [] as ModuleItem[],
  });

  /**
   * search select 过滤参数
   */
  const searchSelectData = [{
    name: t('主访问入口'),
    id: 'domain',
  }, {
    name: 'IP',
    id: 'ip',
  }, {
    name: t('模块'),
    id: 'db_module_id',
    children: [] as Item[],
  }];
  const filterSearch = computed(() => getSearchSelectorParams(listState.filters.search));

  /**
   * 获取表头
   */
  const fetchTableFields = () => {
    listState.fieldsLoading = true;
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      type: props.clusterType,
    };
    return getTableFields(params)
      .then((res) => {
        listState.fields = res;
      })
      .finally(() => {
        listState.fieldsLoading = false;
      });
  };

  /**
   * 获取列表
   */
  const fetchResources = (extra: FetchParams = {}) => {
    const params = {
      dbType: DBTypes.MYSQL,
      bk_biz_id: globalBizsStore.currentBizId,
      type: props.clusterType,
      limit: listState.pagination.limit,
      offset: listState.pagination.limit * (listState.pagination.current - 1),
      ...filterSearch.value,
      ...extra,
    };
    listState.loading = true;
    return getResources<ResourceItem>(params)
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
        listState.loading = false;
      });
  };

  /**
   * change page
   */
  const handleChangePage = (value: number) => {
    listState.pagination.current = value;
    fetchResources();
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

  /**
   * 获取模块列表
   */
  const fetchModules = () => {
    getModules({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: props.clusterType,
    }).then((res) => {
      listState.moduleList = res || [];
      // 设置 search data
      const children = listState.moduleList.map(item => ({ id: String(item.db_module_id), name: item.name }));
      searchSelectData[2].children !== undefined && searchSelectData[2].children.push(...children);
    });
  };

  return {
    listState,
    searchSelectData,
    fetchTableFields,
    fetchResources,
    fetchModules,
    handleChangePage,
    handeChangeLimit,
    handleChangeValues,
  };
}
