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
import { useRequest } from 'vue-request';

import { getHostTodoCount } from '@services/source/ticket';

import { useUserProfile } from '@stores';

const getContext = () => {
  const { isDba } = useUserProfile();

  const { data, run: runGetHostTodoCount } = useRequest(getHostTodoCount, {
    manual: true,
  });

  const faultCount = computed(() => (data && data.value ? data.value.fault_count : 0));
  const recycleCount = computed(() => (data && data.value ? data.value.recycle_count : 0));
  const totalCount = computed(() => faultCount.value + recycleCount.value);

  if (isDba) {
    runGetHostTodoCount();
  }

  return {
    faultCount,
    recycleCount,
    run: runGetHostTodoCount,
    totalCount,
  };
};

let context: ReturnType<typeof getContext> | undefined;

/**
 * 主机待办统计数据
 */
export const useHostTodoCount = () => {
  const route = useRoute();
  if (!context) {
    context = getContext();
  }
  onBeforeUnmount(() => {
    setTimeout(() => {
      if (route.name !== 'resourceManageHostTodo') {
        context = undefined;
      }
    });
  });
  return context;
};
