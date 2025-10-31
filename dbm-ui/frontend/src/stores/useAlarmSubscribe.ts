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

import { defineStore } from 'pinia';

import { getSubscribeList, getSubscribeMetrics } from '@services/source/monitorSubscribe';

import { clusterTypeInfos } from '@common/const';

/**
 * 告警订阅
 */
export const useAlarmSubscribe = defineStore('useAlarmSubscribe', {
  state: () => ({
    metricsMap: {} as Record<
      string,
      {
        displayName: string;
        list: string[];
      }
    >,
    subscribedDomainInfo: {
      dataList: [] as ServiceReturnType<typeof getSubscribeList>['results'],
      dataSet: new Set<string>(),
    },
  }),
  actions: {
    init() {
      this.initMetricsMap();
      this.initSubscribedDomainInfo();
    },
    async initMetricsMap() {
      const clusterTypeNameMap = Object.values(clusterTypeInfos).reduce<Record<string, string>>(
        (dataMap, item) =>
          Object.assign(dataMap, {
            [item.id]: item.name,
          }),
        {},
      );
      const dataMap = await getSubscribeMetrics();
      Object.keys(clusterTypeNameMap).forEach((key) => {
        this.metricsMap[key] = {
          displayName: clusterTypeNameMap[key],
          list: dataMap[key] || [],
        };
      });
    },
    async initSubscribedDomainInfo() {
      const { results } = await getSubscribeList();
      this.subscribedDomainInfo.dataList = results;
      this.subscribedDomainInfo.dataSet.clear();
      results.forEach((item) => {
        this.subscribedDomainInfo.dataSet.add(item.master_domain);
      });
    },
  },
});
