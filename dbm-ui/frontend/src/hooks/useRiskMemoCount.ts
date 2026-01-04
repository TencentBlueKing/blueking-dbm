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

import { getRiskMemoList } from '@services/source/riskMemo';

import { useUserProfile } from '@stores';

/**
 * 告警事件统计数据
 */
export const useRiskMemoCount = () => {
  const { isDba } = useUserProfile();

  const todoCount = ref(0);
  const assistCount = ref(0);

  useRequest(getRiskMemoList, {
    cacheKey: 'riskMemoCount',
    defaultParams: [
      {
        is_assist: false,
        status: 'backlog',
      },
    ],
    manual: !isDba,
    onSuccess(result) {
      todoCount.value = result.count ?? 0;
    },
  });
  useRequest(getRiskMemoList, {
    cacheKey: 'riskMemoAssistCount',
    defaultParams: [
      {
        is_assist: true,
        status: 'backlog',
      },
    ],
    manual: !isDba,
    onSuccess(result) {
      assistCount.value = result.count ?? 0;
    },
  });

  return {
    assistCount,
    todoCount,
  };
};
