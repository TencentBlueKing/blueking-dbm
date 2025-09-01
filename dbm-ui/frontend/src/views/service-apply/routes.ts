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

import { registerBusinessModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    path: 'service-apply',
    name: 'serviceApply',
    meta: {
      navName: t('部署申请'),
    },
    redirect: {
      name: 'serviceApplyIndex',
    },
    children: [
      {
        path: 'index',
        name: 'serviceApplyIndex',
        meta: {
          navName: t('部署申请'),
        },
        component: () => import('@views/service-apply/index/Index.vue'),
      },
      {
        path: 'single',
        name: 'SelfServiceApplySingle',
        meta: {
          navName: t('申请MySQL单节点部署'),
        },
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
      },
      {
        path: 'ha',
        name: 'SelfServiceApplyHa',
        meta: {
          navName: t('申请MySQL主从部署'),
        },
        component: () => import('@views/db-manage/mysql/apply/ApplyMySQL.vue'),
      },
      {
        path: 'tendbcluster',
        name: 'spiderApply',
        meta: {
          navName: t('申请TendbCluster分布式集群部署'),
        },
        component: () => import('@views/db-manage/tendb-cluster/apply/Index.vue'),
      },
      {
        path: 'redis',
        name: 'SelfServiceApplyRedis',
        meta: {
          navName: t('申请Redis集群部署'),
        },
        component: () => import('@views/db-manage/redis/apply/ApplyRedis.vue'),
      },
      {
        path: 'redis-ha',
        name: 'SelfServiceApplyRedisHa',
        meta: {
          navName: t('申请 Redis 主从部署'),
        },
        component: () => import('@views/db-manage/redis/apply-ha/Index.vue'),
      },
      {
        path: 'es',
        name: 'EsApply',
        meta: {
          navName: t('申请ES集群部署'),
        },
        component: () => import('@views/db-manage/elastic-search/apply/Index.vue'),
      },
      {
        path: 'kafka',
        name: 'KafkaApply',
        meta: {
          navName: t('申请Kafka集群部署'),
        },
        component: () => import('@views/db-manage/kafka/apply/Index.vue'),
      },
      {
        path: 'hdfs',
        name: 'HdfsApply',
        meta: {
          navName: t('申请HDFS集群部署'),
        },
        component: () => import('@views/db-manage/hdfs/apply/Index.vue'),
      },
      {
        path: 'pulsar',
        name: 'PulsarApply',
        meta: {
          navName: t('申请Pulsar集群部署'),
        },
        component: () => import('@views/db-manage/pulsar/apply/index.vue'),
      },
      {
        path: 'influxdb',
        name: 'SelfServiceApplyInfluxDB',
        meta: {
          navName: t('申请InfluxDB集群部署'),
        },
        component: () => import('@views/db-manage/influxdb/apply/index.vue'),
      },
      {
        path: 'riak',
        name: 'RiakApply',
        meta: {
          navName: t('申请Riak集群部署'),
        },
        component: () => import('@views/db-manage/riak/apply/Index.vue'),
      },
      {
        path: 'mongodb-shared-cluster-apply',
        name: 'MongoDBSharedClusterApply',
        meta: {
          navName: t('申请MongoDB分片集群部署'),
        },
        component: () => import('@views/db-manage/mongodb/shared-cluster-apply/Index.vue'),
      },
      {
        path: 'mongodb-replica-set-apply',
        name: 'MongoDBReplicaSetApply',
        meta: {
          navName: t('申请MongoDB副本集部署'),
        },
        component: () => import('@views/db-manage/mongodb/replica-set-apply/Index.vue'),
      },
      {
        path: 'doris',
        name: 'DorisApply',
        meta: {
          navName: t('申请Doris集群部署'),
        },
        component: () => import('@views/db-manage/doris/apply/Index.vue'),
      },
      {
        path: 'create-db-module/:type/:bk_biz_id/',
        name: 'SelfServiceCreateDbModule',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
      },
      {
        path: 'bind-db-module/:type/:bk_biz_id/:db_module_id',
        name: 'SelfServiceBindDbModule',
        meta: {
          navName: t('绑定配置'),
        },
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
      },
      {
        path: 'sqlserver-single',
        name: 'SqlServiceSingleApply',
        meta: {
          navName: t('申请SQLServer单节点部署'),
        },
        component: () => import('@views/db-manage/sqlserver/apply/SqlServer.vue'),
      },
      {
        path: 'sqlserver-ha',
        name: 'SqlServiceHaApply',
        meta: {
          navName: t('申请SQLServer主从部署'),
        },
        component: () => import('@views/db-manage//sqlserver/apply/SqlServer.vue'),
      },
      {
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
        name: 'SqlServerCreateDbModule',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/service-apply/create-db-module/SqlServerCreateDbModule.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  if (checkDbConsole('personalWorkbench.serviceApply')) {
    registerBusinessModule([
      {
        path: 'service-apply',
        name: 'BussinessServiceApply',
        meta: {
          navName: t('部署申请'),
        },
        redirect: {
          name: 'BussinessServiceApplyIndex',
        },
        children: [
          {
            path: 'index',
            name: 'BussinessServiceApplyIndex',
            meta: {
              navName: t('部署申请'),
            },
            component: () => import('@views/service-apply/index/Index.vue'),
          },
        ],
      },
    ]);
  }

  return checkDbConsole('personalWorkbench.serviceApply') ? routes : [];
}
