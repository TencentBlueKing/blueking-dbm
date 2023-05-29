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

import {
  type Ref,
  ref,
} from 'vue';

import type {
  HostDetails,
} from '@services/types/ip';

import { useDebouncedRef } from '@hooks';

import { encodeRegexp } from '@utils';

export default function (originalData: Ref<Array<HostDetails>>) {
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    align: 'right',
  });

  const searchKey = useDebouncedRef('');

  const serachList = computed(() => {
    if (!searchKey.value) {
      return originalData.value;
    }
    const searchRule = new RegExp(encodeRegexp(searchKey.value), 'i');
    return originalData.value.reduce((result, item) => {
      if (searchRule.test(item.ip)) {
        result.push(item);
      }
      return result;
    }, [] as Array<HostDetails>);
  });

  const isShowPagination = ref(false);

  const data = computed(() => serachList.value.slice(
    (pagination.current - 1) * pagination.limit,
    pagination.limit * pagination.current,
  ));

  const handlePaginationCurrentChange = (current: number) => {
    pagination.current = current;
  };
  const handlePaginationLimitChange = (limit: number) => {
    pagination.limit = limit;
  };

  watch(searchKey, () => {
    pagination.current = 1;
  });
  watch(serachList, (list) => {
    pagination.count = list.length;
    isShowPagination.value = list.length > 0 && list.length > pagination.limit;
  }, {
    immediate: true,
  });

  return {
    data,
    searchKey,
    serachList,
    isShowPagination,
    pagination,
    handlePaginationCurrentChange,
    handlePaginationLimitChange,
  };
}
