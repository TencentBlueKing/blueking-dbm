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

import { getReportCount } from '@services/source/report';

/**
 * 巡检报告统计数据
 */
export const useReportCount = () => {
  const manageCount = ref(0);
  const assistCount = ref(0);
  const dbReportCountMap = ref<
    Record<
      string,
      {
        assistCount: number;
        manageCount: number;
      }
    >
  >({});

  useRequest(getReportCount, {
    onSuccess(countResult) {
      let manages = 0;
      let assists = 0;
      Object.entries(countResult).forEach(([db, value]) => {
        const singleDbCount = Object.values(value).reduce(
          (results, item) => {
            Object.assign(results, {
              manageCount: item.manage_count + results.manageCount,
              assistCount: item.assist_count + results.assistCount,
            });
            return results;
          },
          {
            manageCount: 0,
            assistCount: 0,
          },
        );
        dbReportCountMap.value[db] = singleDbCount;
        manages = manages + singleDbCount.manageCount;
        assists = assists + singleDbCount.assistCount;
      });
      manageCount.value = manages;
      assistCount.value = assists;
    },
  });

  return {
    manageCount,
    assistCount,
    dbReportCountMap,
  };
};
