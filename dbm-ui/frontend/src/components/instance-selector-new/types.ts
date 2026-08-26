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

import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
import RedisInstanceModel from '@services/model/redis/redis-instance';
import SqlserverHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
import SqlserverSingleInstanceModel from '@services/model/sqlserver/sqlserver-single-instance';
import TendbClusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';

import { ClusterTypes } from '@common/const';

export type ISupportClusterType =
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.REDIS
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBSINGLE;

export interface ClusterTypeRelateInstanceModel {
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbInstanceModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbInstanceModel;
  [ClusterTypes.REDIS]: RedisInstanceModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaInstanceModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleInstanceModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterInstanceModel;
  [ClusterTypes.TENDBHA]: TendbhaInstanceModel;
  [ClusterTypes.TENDBSINGLE]: TendbhaInstanceModel;
}

export type InstanceModel<T extends ISupportClusterType> = ClusterTypeRelateInstanceModel[T];
