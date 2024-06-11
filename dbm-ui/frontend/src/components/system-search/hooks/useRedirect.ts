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

import { useLocation } from '@hooks';

export const useRedirect = () => {
  const location = useLocation();

  const routerNameMap = {
    TwemproxyRedisInstance: 'DatabaseRedisList',
    PredixyTendisplusCluster: 'DatabaseRedisList',
    TwemproxyTendisSSDInstance: 'DatabaseRedisList',
    PredixyRedisCluster: 'DatabaseRedisList',
    RedisInstance: 'DatabaseRedisHaList',
    tendbha: 'DatabaseTendbha',
    tendbsingle: 'DatabaseTendbsingle',
    tendbcluster: 'tendbClusterList',
    es: 'EsList',
    kafka: 'KafkaList',
    hdfs: 'HdfsList',
    pulsar: 'PulsarList',
    redis: 'DatabaseRedisList',
    riak: 'RiakList',
    influxdb: 'InfluxDBInstDetails',
    sqlserver_ha: 'SqlServerHaClusterList',
    sqlserver_single: 'SqlServerSingle',
    MongoShardedCluster: 'MongoDBSharedClusterList',
    MongoReplicaSet: 'MongoDBReplicaSetList',
    doris: 'DorisList',
  } as Record<string, string>;

  return (clusterType: string, queryParams: Record<string, any>, bizId: number) => {
    if (!routerNameMap[clusterType]) {
      return;
    }

    location(
      {
        name: routerNameMap[clusterType],
        query: queryParams,
      },
      bizId,
    );
  };
};
