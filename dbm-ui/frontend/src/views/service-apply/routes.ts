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

import { DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createApplyRoute } from '@utils';

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
    component: () => import('@views/service-apply/Index.vue'),
    children: [
      {
        path: 'index',
        name: 'serviceApplyIndex',
        meta: {
          navName: t('部署申请'),
        },
        component: () => import('@views/service-apply/index/Index.vue'),
      },
      createApplyRoute(DBTypes.MYSQL, TicketTypes.MYSQL_SINGLE_APPLY, t('申请MySQL单节点部署')),
      createApplyRoute(DBTypes.MYSQL, TicketTypes.MYSQL_HA_APPLY, t('申请MySQL主从部署')),
      createApplyRoute(DBTypes.TENDBCLUSTER, TicketTypes.TENDBCLUSTER_APPLY, t('申请TendbCluster分布式集群部署')),
      createApplyRoute(DBTypes.SQLSERVER, TicketTypes.SQLSERVER_SINGLE_APPLY, t('申请SQLServer单节点部署')),
      createApplyRoute(DBTypes.SQLSERVER, TicketTypes.SQLSERVER_HA_APPLY, t('申请SQLServer主从部署')),
      createApplyRoute(DBTypes.REDIS, TicketTypes.REDIS_CLUSTER_APPLY, t('申请Redis集群部署')),
      createApplyRoute(DBTypes.REDIS, TicketTypes.REDIS_INS_APPLY, t('申请 Redis 主从部署')),
      createApplyRoute(DBTypes.MONGODB, TicketTypes.MONGODB_REPLICASET_APPLY, t('申请MongoDB副本集部署')),
      createApplyRoute(DBTypes.MONGODB, TicketTypes.MONGODB_SHARD_APPLY, t('申请MongoDB分片集群部署')),
      createApplyRoute(DBTypes.ES, TicketTypes.ES_APPLY, t('申请ES集群部署')),
      createApplyRoute(DBTypes.KAFKA, TicketTypes.KAFKA_APPLY, t('申请Kafka集群部署')),
      createApplyRoute(DBTypes.HDFS, TicketTypes.HDFS_APPLY, t('申请HDFS集群部署')),
      createApplyRoute(DBTypes.PULSAR, TicketTypes.PULSAR_APPLY, t('申请Pulsar集群部署')),
      createApplyRoute(DBTypes.INFLUXDB, TicketTypes.INFLUXDB_APPLY, t('申请InfluxDB集群部署')),
      createApplyRoute(DBTypes.RIAK, TicketTypes.RIAK_CLUSTER_APPLY, t('申请Riak集群部署')),
      createApplyRoute(DBTypes.DORIS, TicketTypes.DORIS_APPLY, t('申请Doris集群部署')),
      createApplyRoute(DBTypes.K8S_SURREALDB, TicketTypes.K8S_SURREALDB_HA_APPLY, t('申请 SurrealDB 集群部署')),
      createApplyRoute(DBTypes.K8S_SURREALDB, TicketTypes.K8S_SURREALDB_SINGLE_APPLY, t('申请 SurrealDB 单节点部署')),
      createApplyRoute(DBTypes.K8S_QRRANT, TicketTypes.K8S_QDRANT_HA_APPLY, t('申请 Qdrant 集群部署')),
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
