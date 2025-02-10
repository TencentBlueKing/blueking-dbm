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

import { queryBizClusterAttrs, queryResourceAdministrationAttrs } from '@services/source/dbbase';

import { useGlobalBizs } from '@stores';

import { ClusterTypes } from '@common/const';
import { batchSplitRegex, domainPort, domainRegex, ipPort, ipv4 } from '@common/regex';

type QueryBizClusterAttrsReturnType = ServiceReturnType<typeof queryBizClusterAttrs>;

export type SearchAttrs = Record<
  string,
  {
    id: string;
    name: string;
  }[]
>;

type ColumnCheckedMap = Record<string, string[]>;

export const useLinkQueryColumnSerach = (config: {
  searchType: string;
  attrs: string[];
  fetchDataFn?: () => void;
  isCluster?: boolean;
  isQueryAttrs?: boolean;
  defaultSearchItem?: {
    id: string;
    name: string;
  };
  isDiscardNondefault?: boolean;
  initAutoFetch?: boolean;
}) => {
  const {
    searchType,
    attrs,
    fetchDataFn = () => {},
    isCluster = true,
    isQueryAttrs = true,
    defaultSearchItem,
    isDiscardNondefault = false,
    initAutoFetch = true,
  } = config;
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const searchValue = ref<ISearchValue[]>([]);
  const columnAttrs = ref<QueryBizClusterAttrsReturnType>({});
  const searchAttrs = ref<SearchAttrs>({});
  // 表格列已勾选的映射
  const columnCheckedMap = ref<ColumnCheckedMap>({});

  const batchSearchIpInatanceList = computed(() => {
    const batchObjList = searchValue.value.filter((item) => ['ip', 'instance'].includes(item.id));
    if (batchObjList.length > 0) {
      return _.flatMap(batchObjList.map((item) => item.values!.map((value) => value.id)));
    }
    return [];
  });

  const isFilter = computed(() => searchValue.value.length > 0);

  const resourceTypes = ['spotty_host', 'resource_record'];

  const sortValue: {
    ordering?: string;
  } = {};

  if (isQueryAttrs) {
    let requestHandler;
    if (resourceTypes.includes(searchType)) {
      requestHandler = queryResourceAdministrationAttrs({
        resource_type: searchType,
      });
    } else {
      const attrsObj = isCluster
        ? {
            cluster_attrs: attrs.join(','),
          }
        : {
            instances_attrs: attrs.join(','),
          };

      // 查询表头筛选列表
      requestHandler = queryBizClusterAttrs({
        bk_biz_id: currentBizId,
        cluster_type: searchType as ClusterTypes,
        ...attrsObj,
      });
    }

    requestHandler.then((resultObj) => {
      columnAttrs.value = resultObj;
      searchAttrs.value = Object.entries(resultObj).reduce((results, item) => {
        Object.assign(results, {
          [item[0]]: item[1].map((item) => ({
            id: item.value,
            name: item.text,
          })),
        });
        return results;
      }, {} as SearchAttrs);
    });
  }

  onMounted(() => {
    if (initAutoFetch) {
      fetchDataFn();
    }
  });

  // 表头筛选
  const columnFilterChange = (data: {
    checked: string[];
    column: {
      field: string;
      label: string;
      filter: {
        checked: string[];
        list: {
          value: string;
          text: string;
        }[];
      };
    };
    index: number;
  }) => {
    // console.log('???', data);
    // if (!data.column.filter.checked) {
    //   return;
    // }
    if (data.checked.length === 0) {
      searchValue.value = searchValue.value.filter((item) => item.id !== data.column.field);
      fetchDataFn();
      return;
    }

    const columnSearchObj = {
      id: data.column.field,
      name: data.column.label,
      values: data.checked.map((item) => ({
        id: item,
        name: data.column.filter.list.find((row) => row.value === item)?.text ?? '',
      })),
    };

    const index = searchValue.value.findIndex((item) => item.id === data.column.field);
    if (index > -1) {
      // 已存在，替换旧值
      searchValue.value.splice(index, 1, columnSearchObj);
    } else {
      searchValue.value.push(columnSearchObj);
    }
    fetchDataFn();
  };

  // 表头排序
  const columnSortChange = (data: {
    column: {
      field: string;
      label: string;
    };
    index: number;
    type: 'asc' | 'desc' | 'null';
  }) => {
    if (data.type === 'asc') {
      sortValue.ordering = data.column.field;
    } else if (data.type === 'desc') {
      sortValue.ordering = `-${data.column.field}`;
    } else {
      delete sortValue.ordering;
    }
    fetchDataFn();
  };

  // 搜索框输入校验
  const validateSearchValues = (
    item: { id: string } | null,
    values: ISearchValue['values'],
  ): Promise<true | string> => {
    if (!item) {
      return Promise.resolve(true);
    }
    // console.log('valid values>>', item, values);
    if (values) {
      if (['instance', 'ip'].includes(item.id)) {
        const list = values[0].id.split(batchSplitRegex);
        if (list.some((ip) => !ipPort.test(ip) && !ipv4.test(ip))) {
          return Promise.resolve(t('格式错误'));
        }
      }
      if (item.id === 'domain') {
        const list = values[0].id.split(batchSplitRegex);
        if (list.length === 1) {
          return Promise.resolve(true);
        }

        if (list.some((ip) => !domainRegex.test(ip) && !domainPort.test(ip))) {
          return Promise.resolve(t('格式错误'));
        }
      }
      return Promise.resolve(true);
    }
    return Promise.resolve(t('格式错误'));
  };

  const handleSearchValueChange = (valueList: ISearchValue[]) => {
    // console.log('search>>>', valueList);
    if (valueList.length === 1) {
      // 检查是否默认搜索
      const [item] = valueList;
      if (!item.values) {
        // 默认搜索，使用默认id
        const value = item.id;
        const values = value.split(' | ');
        // 要么命中IP，否则都默认按域名处理
        const instanceList: string[] = [];
        const defaultList: string[] = [];
        values.forEach((value) => {
          if (ipPort.test(value) || ipv4.test(value)) {
            instanceList.push(value);
            return;
          }
          defaultList.push(value);
        });
        valueList.length = 0;
        if (isDiscardNondefault) {
          // 丢弃非默认
          if (['instance', 'ip'].includes(defaultSearchItem?.id ?? '')) {
            defaultList.length = 0;
          } else if (defaultSearchItem?.id === 'domain') {
            instanceList.length = 0;
          }
        }
        if (defaultList.length > 0) {
          const defaultItem = {
            id: defaultSearchItem?.id || item.id,
            name: defaultSearchItem?.name || item.name,
            values: defaultList.map((item) => ({
              id: item,
              name: item,
            })),
          };
          valueList.push(defaultItem);
        }
        if (instanceList.length > 0) {
          const instanceSearchItem = {
            id: defaultSearchItem?.id === 'ip' ? 'ip' : 'instance',
            name: defaultSearchItem?.id === 'ip' ? 'IP' : 'instance',
            values: instanceList.map((item) => ({
              id: item,
              name: item,
            })),
          };
          valueList.push(instanceSearchItem);
        }
      }
    }
    columnCheckedMap.value = valueList.reduce((results, item) => {
      Object.assign(results, {
        [item.id]: item.values?.map((value) => value.id) ?? [],
      });
      return results;
    }, {} as ColumnCheckedMap);
    // 防止方法由于searchValue的值改变而被循环触发
    if (JSON.stringify(valueList) === JSON.stringify(searchValue.value)) {
      return;
    }

    // 批量参数统一用,分隔符，展示的分隔符统一成 |
    const handledValueList: ISearchValue[] = [];
    valueList.forEach((item) => {
      if (!['domain', 'instance', 'ip'].includes(item.id)) {
        // 非域名/ip类，原样返回
        handledValueList.push(item);
        return;
      }
      const values = item.values
        ? item.values.reduce(
            (results, value) => {
              const idList = _.uniq(`${value.id.trim()}`.split(batchSplitRegex));
              const nameList = _.uniq(`${value.name.trim()}`.split(batchSplitRegex));
              results.push(
                ...idList.map((id, index) => ({
                  id,
                  name: nameList[index],
                })),
              );
              return results;
            },
            [] as {
              id: string;
              name: string;
            }[],
          )
        : [];

      const searchObj = {
        ...item,
        values,
      };

      if (item.id === 'domain') {
        // 搜索访问入口，前端去除端口
        searchObj.values = searchObj.values?.map((value) => ({
          id: value.id.split(':')[0],
          name: value.name,
        }));
      }
      handledValueList.push(searchObj);
    });

    searchValue.value = handledValueList;
    fetchDataFn();
  };

  /**
   * 清空搜索
   */
  const clearSearchValue = () => {
    searchValue.value = [];
    fetchDataFn();
  };

  return {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    batchSearchIpInatanceList,
    isFilter,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  };
};
