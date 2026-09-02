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

import { getRedisMachineList } from '@services/source/redis';
import { getMachineList as getSqlserverhaMachineList } from '@services/source/sqlserveHaCluster';
import { getTendbclusterMachineList } from '@services/source/tendbcluster';
import { getTendbhaMachineList } from '@services/source/tendbha';
import { getTendbSingleMachineList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

import type { ISupportHostType } from './types';

// 主机类型 → 默认数据源（machine list 接口）
// 角色过滤不做默认值，全部由调用方通过 dataSourceMap 覆盖时显式传入（如 instance_role: 'backend_master'）
export const hostMachineDataSourceMap: Record<ISupportHostType, (params: any) => Promise<any>> = {
  [ClusterTypes.REDIS]: getRedisMachineList,
  [ClusterTypes.SQLSERVER_HA]: getSqlserverhaMachineList,
  [ClusterTypes.SQLSERVER_SINGLE]: getSqlserverhaMachineList,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterMachineList,
  [ClusterTypes.TENDBHA]: getTendbhaMachineList,
  [ClusterTypes.TENDBSINGLE]: getTendbSingleMachineList,
};
