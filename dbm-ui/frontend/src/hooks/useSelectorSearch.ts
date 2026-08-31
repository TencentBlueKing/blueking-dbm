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
import { queryBizClusterAttrs } from '@services/source/dbbase';

import { useGlobalBizs } from '@stores';

export type SearchAttrs = Record<
  string,
  {
    id: string;
    name: string;
  }[]
>;

/**
 * 集群/实例选择器搜索：维护 DbQuickSearch 的搜索值与远程候选项
 */
export const useSelectorSearch = (clusterType: string, attrs: string[]) => {
  const { currentBizId } = useGlobalBizs();

  const searchValue = ref<Record<string, string>>({});
  const searchAttrs = ref<SearchAttrs>({});
  const columnAttrs = ref<Record<string, { text: string; value: string }[]>>({});

  queryBizClusterAttrs({
    bk_biz_id: currentBizId,
    cluster_attrs: attrs.join(','),
    cluster_type: clusterType,
  }).then((result) => {
    columnAttrs.value = result;
    searchAttrs.value = Object.keys(result).reduce<SearchAttrs>((results, key) => {
      Object.assign(results, {
        [key]: result[key].map((item) => ({
          id: item.value,
          name: item.text,
        })),
      });
      return results;
    }, {});
  });

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
  };

  const clearSearchValue = () => {
    searchValue.value = {};
  };

  return {
    clearSearchValue,
    columnAttrs,
    handleFilterChange,
    searchAttrs,
    searchValue,
  };
};
