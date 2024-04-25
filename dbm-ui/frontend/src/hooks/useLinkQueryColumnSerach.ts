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
import _ from 'lodash';
import { useI18n } from 'vue-i18n';

import { queryBizClusterAttrs } from '@services/source/dbbase';

import { useGlobalBizs } from '@stores';

import type { ClusterTypes } from '@common/const';
import {
  batchSplitRegex,
  domainPort,
  domainRegex,
  ipPort,
  ipv4,
} from '@common/regex';

type QueryBizClusterAttrsReturnType = ServiceReturnType<typeof queryBizClusterAttrs>;

export type SearchAttrs = Record<string, {
  id: string,
  name: string,
}[]>;

type ColumnCheckedMap = Record<string, string[]>;

export const useLinkQueryColumnSerach = (
  clusterType: ClusterTypes,
  attrs: string[],
  fetchDataFn?: () => void,
  isCluster = true,
) => {
  const queryTableDataFn = fetchDataFn ? fetchDataFn : () => {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const searchValue = ref<ISearchValue[]>([]);
  const columnAttrs = ref<QueryBizClusterAttrsReturnType>({});
  const searchAttrs = ref<SearchAttrs>({});
  // 表格列已勾选的映射
  const columnCheckedMap = ref<ColumnCheckedMap>({});

  const batchSearchIpInatanceList = computed(() => {
    const batchObjList = searchValue.value.filter(item => ['ip', 'instance'].includes(item.id));
    if (batchObjList.length > 0) {
      return _.flatMap(batchObjList.map(item => item.values!.map(value => value.id)));
    }
    return [];
  });

  const sortValue: {
    ordering?: string,
  } = {};

  const attrsObj = isCluster ? {
    cluster_attrs: attrs.join(','),
  } : {
    instances_attrs: attrs.join(','),
  };

  // 查询表头筛选列表
  queryBizClusterAttrs({
    bk_biz_id: currentBizId,
    cluster_type: clusterType,
    ...attrsObj,
  }).then((resultObj) => {
    columnAttrs.value = resultObj;
    searchAttrs.value = Object.entries(resultObj).reduce((results, item) => {
      Object.assign(results, {
        [item[0]]: item[1].map(item => ({
          id: item.value,
          name: item.text,
        })),
      });
      return results;
    }, {} as SearchAttrs);
  });

  onMounted(() => {
    queryTableDataFn();
  });

  // 表头筛选
  const columnFilterChange = (data: {
    checked: string[];
    column: {
      field: string;
      label: string;
      filter: {
        checked: string[],
        list: {
          value: string,
          text: string,
        }[]
      }
    };
    index: number;
  }) => {
    // console.log('filtervalue>>>', data);
    if (!data.column.filter.checked) {
      return;
    }
    if (data.checked.length === 0) {
      searchValue.value = searchValue.value.filter(item => item.id !== data.column.field);
      queryTableDataFn();
      return;
    }

    const columnSearchObj = {
      id: data.column.field,
      name: data.column.label,
      values: data.checked.map(item => ({
        id: item,
        name: data.column.filter.list.find(row => row.value === item)?.text ?? '',
      })),
    };

    const index = searchValue.value.findIndex(item => item.id === data.column.field);
    if (index > -1) {
      // 已存在，替换旧值
      searchValue.value.splice(index, 1, columnSearchObj);
    } else {
      searchValue.value.push(columnSearchObj);
    }
    queryTableDataFn();
  };

  // 表头排序
  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null'
  }) => {
    if (data.type === 'asc') {
      sortValue.ordering = data.column.field;
    } else if (data.type === 'desc') {
      sortValue.ordering = `-${data.column.field}`;
    } else {
      delete sortValue.ordering;
    }
    queryTableDataFn();
  };

  // 搜索框输入校验
  const validateSearchValues = (item: {id: string}, values: ISearchValue['values']): Promise<true | string> => {
    // console.log('valid values>>', values);
    if (values) {
      if (['instance', 'ip'].includes(item.id)) {
        const list = values[0].id.split(batchSplitRegex);
        if (list.some(ip => !ipPort.test(ip) && !ipv4.test(ip))) {
          return Promise.resolve(t('格式错误'));
        }
      }
      if (item.id === 'domain') {
        const list = values[0].id.split(batchSplitRegex);
        if (list.some(ip => !domainRegex.test(ip) && !domainPort.test(ip))) {
          return Promise.resolve(t('格式错误'));
        }
      }
      return Promise.resolve(true);
    }
    return Promise.resolve(t('格式错误'));
  };

  const handleSearchValueChange = (valueList: ISearchValue[]) => {
    // console.log('search>>>', valueList);
    columnCheckedMap.value = valueList.reduce((results, item) => {
      Object.assign(results, {
        [item.id]: item.values?.map(value => value.id) ?? [],
      });
      return results;
    }, {} as ColumnCheckedMap);
    // 防止方法由于searchValue的值改变而被循环触发
    if (JSON.stringify(valueList) === JSON.stringify(searchValue.value)) {
      return;
    }

    // 批量参数统一用,分隔符，展示的分隔符统一成 |
    const handledValueList: ISearchValue[] = [];
    // console.log('valueList>>>', valueList);
    valueList.forEach((item) => {
      const values = item.values ? item.values.reduce((results, value) => {
        const idList = _.uniq(`${value.id}`.split(batchSplitRegex));
        const nameList = _.uniq(`${value.name}`.split(batchSplitRegex));
        results.push(...idList.map((id, index) => ({
          id,
          name: nameList[index],
        })));
        return results;
      }, [] as {
        id: string;
        name: string;
      }[]) : [];

      const searchObj = {
        ...item,
        values,
      };

      if (item.id === 'domain') {
        // 搜索访问入口，前端去除端口
        searchObj.values = searchObj.values?.map(value => ({
          id: value.id.split(':')[0],
          name: value.name,
        }));
      }
      handledValueList.push(searchObj);
    });

    searchValue.value = handledValueList;
    console.log('searchValue.value>>>', searchValue.value);
    queryTableDataFn();
  };

  /**
   * 清空搜索
   */
  const clearSearchValue = () => {
    searchValue.value = [];
    queryTableDataFn();
  };

  return {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  };
};
