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

export default <T extends Record<string, any>>(config: {
  list?: T[];
  remoteMethod?: (params: {
    defaultValue?: string;
    keyword?: string;
  }) => Promise<{ label: string; value: number | string }[]>;
  remoteSearch?: boolean;
}) => {
  const filterKey = ref('');
  const remoteList = shallowRef<T[]>([]);
  const isLoading = ref(false);

  const isRemoteList = computed(() => _.isFunction(config.remoteMethod));

  const list = computed(() => {
    if (isRemoteList.value) {
      return remoteList.value;
    }

    return (config.list || []) as T[];
  });

  // 请求序号，只接受最后一次请求的结果，避免先发的慢响应覆盖后发的结果
  let latestRequestId = 0;
  const fetchRemoteList = () => {
    if (!isRemoteList.value) {
      return;
    }

    latestRequestId = latestRequestId + 1;
    const currentRequestId = latestRequestId;

    isLoading.value = true;
    Promise.resolve()
      .then(() =>
        config!.remoteMethod!({
          keyword: filterKey.value,
        }),
      )
      .then((data) => {
        if (currentRequestId !== latestRequestId) {
          return;
        }
        remoteList.value = data as unknown as T[];
      })
      .finally(() => {
        if (currentRequestId === latestRequestId) {
          isLoading.value = false;
        }
      });
  };

  watch(
    filterKey,
    _.debounce(() => {
      if (config.remoteMethod && config.remoteSearch) {
        fetchRemoteList();
      }
    }, 300),
  );

  fetchRemoteList();

  return {
    fetchRemoteList,
    filterKey,
    isRemoteList,
    list,
    loading: isLoading,
    remoteList,
  };
};
