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
    children: [
      {
        component: () => import('@views/service-apply/index/Index.vue'),
        meta: {
          navName: t('服务申请'),
        },
        name: 'serviceApplyIndex',
        path: 'index',
      },
      {
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
        meta: {
          navName: t('申请MySQL单节点部署'),
        },
        name: 'SelfServiceApplySingle',
        path: 'single',
      },
      {
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
        meta: {
          navName: t('申请MySQL主从部署'),
        },
        name: 'SelfServiceApplyHa',
        path: 'ha',
      },
      {
        component: () => import('@views/db-manage/tendb-cluster/apply/Index.vue'),
        meta: {
          navName: t('申请TendbCluster分布式集群部署'),
        },
        name: 'spiderApply',
        path: 'tendbcluster',
      },
      {
        component: () => import('@views/db-manage/redis/apply/ApplyRedis.vue'),
        meta: {
          navName: t('申请Redis集群部署'),
        },
        name: 'SelfServiceApplyRedis',
        path: 'redis',
      },
      {
        component: () => import('@views/db-manage/redis/apply-ha/Index.vue'),
        meta: {
          navName: t('申请 Redis 主从部署'),
        },
        name: 'SelfServiceApplyRedisHa',
        path: 'redis-ha',
      },
      {
        component: () => import('@views/db-manage/elastic-search/apply/Index.vue'),
        meta: {
          navName: t('申请ES集群部署'),
        },
        name: 'EsApply',
        path: 'es',
      },
      {
        component: () => import('@views/db-manage/kafka/apply/Index.vue'),
        meta: {
          navName: t('申请Kafka集群部署'),
        },
        name: 'KafkaApply',
        path: 'kafka',
      },
      {
        component: () => import('@views/db-manage/hdfs/apply/Index.vue'),
        meta: {
          navName: t('申请HDFS集群部署'),
        },
        name: 'HdfsApply',
        path: 'hdfs',
      },
      {
        component: () => import('@views/db-manage/pulsar/apply/index.vue'),
        meta: {
          navName: t('申请Pulsar集群部署'),
        },
        name: 'PulsarApply',
        path: 'pulsar',
      },
      {
        component: () => import('@views/db-manage/influxdb/apply/index.vue'),
        meta: {
          navName: t('申请InfluxDB集群部署'),
        },
        name: 'SelfServiceApplyInfluxDB',
        path: 'influxdb',
      },
      {
        component: () => import('@views/db-manage/riak/apply/Index.vue'),
        meta: {
          navName: t('申请Riak集群部署'),
        },
        name: 'RiakApply',
        path: 'riak',
      },
      {
        component: () => import('@views/db-manage/mongodb/shared-cluster-apply/Index.vue'),
        meta: {
          navName: t('申请MongoDB分片集群部署'),
        },
        name: 'MongoDBSharedClusterApply',
        path: 'mongodb-shared-cluster-apply',
      },
      {
        component: () => import('@views/db-manage/mongodb/replica-set-apply/Index.vue'),
        meta: {
          navName: t('申请MongoDB副本集部署'),
        },
        name: 'MongoDBReplicaSetApply',
        path: 'mongodb-replica-set-apply',
      },
      {
        component: () => import('@views/db-manage/doris/apply/Index.vue'),
        meta: {
          navName: t('申请Doris集群部署'),
        },
        name: 'DorisApply',
        path: 'doris',
      },
      {
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
        meta: {
          navName: t('新建模块'),
        },
        name: 'SelfServiceCreateDbModule',
        path: 'create-db-module/:type/:bk_biz_id/',
      },
      {
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
        meta: {
          navName: t('绑定配置'),
        },
        name: 'SelfServiceBindDbModule',
        path: 'bind-db-module/:type/:bk_biz_id/:db_module_id',
      },
      {
        component: () => import('@views/db-manage/sqlserver/apply/SqlServer.vue'),
        meta: {
          navName: t('申请SQLServer单节点部署'),
        },
        name: 'SqlServiceSingleApply',
        path: 'sqlserver-single',
      },
      {
        component: () => import('@views/db-manage//sqlserver/apply/SqlServer.vue'),
        meta: {
          navName: t('申请SQLServer主从部署'),
        },
        name: 'SqlServiceHaApply',
        path: 'sqlserver-ha',
      },
      {
        component: () => import('@views/service-apply/create-db-module/SqlServerCreateDbModule.vue'),
        meta: {
          navName: t('新建模块'),
        },
        name: 'SqlServerCreateDbModule',
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
      },
    ],
    meta: {
      navName: t('服务申请'),
    },
    name: 'serviceApply',
    path: 'service-apply',
    redirect: {
      name: 'serviceApplyIndex',
    },
  },
];

export default function getRoutes() {
  return checkDbConsole('personalWorkbench.serviceApply') ? routes : [];
}
