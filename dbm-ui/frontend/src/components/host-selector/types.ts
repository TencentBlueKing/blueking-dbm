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

import TendbhaMachineModel from '@services/model/mysql/tendbha-machine';
import TendbSingleMachineModel from '@services/model/mysql/tendbSingle-machine';
import RedisMachineModel from '@services/model/redis/redis-machine';
import SqlserverMachineModel from '@services/model/sqlserver/sqlserver-machine';
import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';

import { ClusterTypes } from '@common/const';

// 主机类型 key 与 ClusterTypes 一一对应（同集群类型的不同角色，如 tendbcluster 的 remote/spider，由调用方通过 dataSourceMap 按角色过滤）
export type ISupportHostType =
  | ClusterTypes.REDIS
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBSINGLE;

export interface ClusterTypeRelateMachineModel {
  [ClusterTypes.REDIS]: RedisMachineModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverMachineModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverMachineModel;
  [ClusterTypes.TENDBCLUSTER]: TendbclusterMachineModel;
  [ClusterTypes.TENDBHA]: TendbhaMachineModel;
  [ClusterTypes.TENDBSINGLE]: TendbSingleMachineModel;
}

export type HostModel<T extends ISupportHostType> = ClusterTypeRelateMachineModel[T];

// 按主机类型分组的选中值结构
export type HostSelectorValues<T extends ISupportHostType> = { [key in T]: HostModel<T>[] };
