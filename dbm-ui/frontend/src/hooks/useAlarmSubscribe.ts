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
import { getSubscribeList, getSubscribeMetrics } from '@services/source/monitorSubscribe';

import { clusterTypeInfos } from '@common/const';

/**
 * 告警订阅
 */

const metricsMap = ref<
  Record<
    string,
    {
      displayName: string;
      list: string[];
    }
  >
>({});
const subscribedDomainInfo = ref<{
  dataList: ServiceReturnType<typeof getSubscribeList>['results'];
  dataSet: Set<string>;
}>({
  dataList: [],
  dataSet: new Set(),
});

export const useAlarmSubscribe = () => {
  const initMetricsMap = async () => {
    const clusterTypeNameMap = Object.values(clusterTypeInfos).reduce<Record<string, string>>(
      (dataMap, item) =>
        Object.assign(dataMap, {
          [item.id]: item.name,
        }),
      {},
    );
    const dataMap = await getSubscribeMetrics();
    Object.keys(clusterTypeNameMap).forEach((key) => {
      metricsMap.value[key] = {
        displayName: clusterTypeNameMap[key],
        list: dataMap[key]?.map((item) => item.name) || [],
      };
    });
  };

  const initSubscribedDomainInfo = async () => {
    const { results } = await getSubscribeList();
    subscribedDomainInfo.value.dataList = results;
    subscribedDomainInfo.value.dataSet.clear();
    results.forEach((item) => {
      subscribedDomainInfo.value.dataSet.add(item.master_domain);
    });
  };

  onMounted(() => {
    initMetricsMap();
    initSubscribedDomainInfo();
  });

  return {
    initMetricsMap,
    initSubscribedDomainInfo,
    metricsMap,
    subscribedDomainInfo,
  };
};
