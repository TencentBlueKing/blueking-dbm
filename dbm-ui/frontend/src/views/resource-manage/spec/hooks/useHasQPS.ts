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

import { computed } from 'vue';

import { ClusterTypes } from '@common/const';

const hasQPSClusterTypes = [
  // `${ClusterTypes.TWEMPROXY_REDIS_INSTANCE}_tendiscache`,
  // `${ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE}_tendisssd`,
  // `${ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER}_tendisplus`,
  `${ClusterTypes.TENDBCLUSTER}_remote`,
  `${ClusterTypes.MONGODB}_shardSvr`,
];

export const useHasQPS = (props: {
  clusterType: string,
  machineType: string
}) => {
  const hasQPS = computed(() => hasQPSClusterTypes.includes(`${props.clusterType}_${props.machineType}`));

  return {
    hasQPS,
  };
};
