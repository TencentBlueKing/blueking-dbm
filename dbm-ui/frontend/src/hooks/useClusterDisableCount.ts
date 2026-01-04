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

import { getClusterDisableCount } from '@services/source/ticket';

/**
 * 集群下架待办列表统计数据
 */
export const useClusterDisableCount = () => {
  const { data, run: runTicketClusterDisableTodoCount } = useRequest(getClusterDisableCount, {
    manual: true,
  });

  const todoCount = computed(() =>
    data && data.value ? Object.values(data.value.todo).reduce((prevCount, item) => prevCount + item, 0) : 0,
  );
  const toAssistCount = computed(() =>
    data && data.value ? Object.values(data.value.to_assist).reduce((prevCount, item) => prevCount + item, 0) : 0,
  );

  runTicketClusterDisableTodoCount();

  return {
    data,
    toAssistCount,
    todoCount,
  };
};
