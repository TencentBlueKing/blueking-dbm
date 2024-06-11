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
import type { RouteRecordRaw } from 'vue-router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'serviceApply',
    path: 'service-apply',
    meta: {
      navName: t('服务申请'),
    },
    redirect: {
      name: 'serviceApplyIndex',
    },
    children: [
      {
        name: 'serviceApplyIndex',
        path: 'index',
        component: () => import('@views/service-apply/index/Index.vue'),
        meta: {
          navName: t('服务申请'),
        },
      },
      {
        name: 'SelfServiceApplySingle',
        path: 'single',
        meta: {
          navName: t('申请MySQL单节点部署'),
        },
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
      },
      {
        name: 'SelfServiceApplyHa',
        path: 'ha',
        meta: {
          navName: t('申请MySQL主从部署'),
        },
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
      },
      {
        name: 'spiderApply',
        path: 'tendbcluster',
        meta: {
          navName: t('申请TendbCluster分布式集群部署'),
        },
        component: () => import('@views/db-manage/tendb-cluster/apply/Index.vue'),
      },
      {
        name: 'SelfServiceApplyRedis',
        path: 'redis',
        meta: {
          navName: t('申请Redis集群部署'),
        },
        component: () => import('@views/db-manage/redis/apply/ApplyRedis.vue'),
      },
      {
        name: 'SelfServiceApplyRedisHa',
        path: 'redis-ha',
        meta: {
          navName: t('申请 Redis 主从部署'),
        },
        component: () => import('@views/db-manage/redis/apply-ha/Index.vue'),
      },
      {
        name: 'EsApply',
        path: 'es',
        meta: {
          navName: t('申请ES集群部署'),
        },
        component: () => import('@views/db-manage/elastic-search/apply/Index.vue'),
      },
      {
        name: 'KafkaApply',
        path: 'kafka',
        meta: {
          navName: t('申请Kafka集群部署'),
        },
        component: () => import('@views/db-manage/kafka/apply/Index.vue'),
      },
      {
        name: 'HdfsApply',
        path: 'hdfs',
        meta: {
          navName: t('申请HDFS集群部署'),
        },
        component: () => import('@views/db-manage/hdfs/apply/Index.vue'),
      },
      {
        name: 'PulsarApply',
        path: 'pulsar',
        meta: {
          navName: t('申请Pulsar集群部署'),
        },
        component: () => import('@views/db-manage/pulsar/apply/index.vue'),
      },
      {
        name: 'SelfServiceApplyInfluxDB',
        path: 'influxdb',
        meta: {
          navName: t('申请InfluxDB集群部署'),
        },
        component: () => import('@views/db-manage/influxdb/apply/index.vue'),
      },
      {
        name: 'RiakApply',
        path: 'riak',
        meta: {
          navName: t('申请Riak集群部署'),
        },
        component: () => import('@views/db-manage/riak/apply/Index.vue'),
      },
      {
        name: 'MongoDBSharedClusterApply',
        path: 'mongodb-shared-cluster-apply',
        meta: {
          navName: t('申请MongoDB分片集群部署'),
        },
        component: () => import('@views/db-manage/mongodb/shared-cluster-apply/Index.vue'),
      },
      {
        name: 'MongoDBReplicaSetApply',
        path: 'mongodb-replica-set-apply',
        meta: {
          navName: t('申请MongoDB副本集部署'),
        },
        component: () => import('@views/db-manage/mongodb/replica-set-apply/Index.vue'),
      },
      {
        name: 'DorisApply',
        path: 'doris',
        meta: {
          navName: t('申请Doris集群部署'),
        },
        component: () => import('@views/db-manage/doris/apply/Index.vue'),
      },
      {
        name: 'SelfServiceCreateDbModule',
        path: 'create-db-module/:type/:bk_biz_id/',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
      },
      {
        name: 'SelfServiceBindDbModule',
        path: 'bind-db-module/:type/:bk_biz_id/:db_module_id',
        meta: {
          navName: t('绑定配置'),
        },
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
      },
      {
        name: 'SqlServiceSingleApply',
        path: 'sqlserver-single',
        meta: {
          navName: t('申请SQLServer单节点部署'),
        },
        component: () => import('@views/db-manage/sqlserver/apply/SqlServer.vue'),
      },
      {
        name: 'SqlServiceHaApply',
        path: 'sqlserver-ha',
        meta: {
          navName: t('申请SQLServer主从部署'),
        },
        component: () => import('@views/db-manage//sqlserver/apply/SqlServer.vue'),
      },
      {
        name: 'SqlServerCreateDbModule',
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/service-apply/create-db-module/SqlServerCreateDbModule.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return checkDbConsole('personalWorkbench.serviceApply') ? routes : [];
}
