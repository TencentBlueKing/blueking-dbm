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

import type { ClusterListOperation } from '@services/types';

import { ClusterTypes } from '@common/const';

export interface TableConfig {
  // 选中项的唯一标识字段，缺省用集群 id，见下方 tendbhaSlave 说明
  rowKey?: string;
  // queryBizClusterAttrs 要拉取的候选项字段，同时决定搜索栏显示哪些搜索条件
  searchAttrs: string[];
  // queryBizClusterAttrs 用的集群类型，从库 tab 要按主集群类型查，缺省取 tab id
  searchClusterType?: string;
}

/**
 * 各集群类型的行数据结构不同，这里只声明选择器表格实际读到的字段。
 * 调用方通过 customColums 整组替换标准列时，行数据可能是完全不同的模型（如 RedisRollbackModel），
 * 那条路径下的列由调用方自己渲染，不经过这里。
 */
export interface ResourceItem {
  bk_cloud_name: string;
  cluster_name: string;
  // Redis 架构版本
  cluster_type_name?: string;
  db_module_name?: string;
  id: number;
  isOffline?: boolean;
  major_version?: string;
  master_domain: string;
  // MySQL 单节点的实例列表
  masters?: { ip: string; port: number }[];
  operations?: ClusterListOperation[];
  status: string;
  sync_mode?: string;
  tags?: { key: string; value: string }[];
}

const MONGO_ATTRS = ['bk_cloud_id', 'major_version', 'region', 'time_zone'];
const ORACLE_ATTRS = ['bk_cloud_id', 'major_version'];
const REDIS_ATTRS = ['bk_cloud_id', 'major_version', 'region', 'time_zone', 'cluster_type'];
const SQLSERVER_ATTRS = ['bk_cloud_id', 'db_module_id', 'major_version'];
const TENDBCLUSTER_ATTRS = ['bk_cloud_id', 'major_version', 'region', 'time_zone'];
const TENDBHA_ATTRS = ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'];

/**
 * 按 tab id 索引，key 与 ClusterSelector 的 tabListMap 一致
 */
export const tableConfigMap: Record<string, TableConfig> = {
  [ClusterTypes.MONGO_REPLICA_SET]: {
    searchAttrs: MONGO_ATTRS,
  },
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    searchAttrs: MONGO_ATTRS,
  },
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: {
    searchAttrs: ORACLE_ATTRS,
  },
  [ClusterTypes.ORACLE_SINGLE_NONE]: {
    searchAttrs: ORACLE_ATTRS,
  },
  [ClusterTypes.REDIS]: {
    searchAttrs: REDIS_ATTRS,
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    searchAttrs: REDIS_ATTRS,
    searchClusterType: ClusterTypes.REDIS,
  },
  [ClusterTypes.SQLSERVER_HA]: {
    searchAttrs: SQLSERVER_ATTRS,
  },
  [ClusterTypes.SQLSERVER_SINGLE]: {
    searchAttrs: SQLSERVER_ATTRS,
  },
  [ClusterTypes.TENDBCLUSTER]: {
    searchAttrs: TENDBCLUSTER_ATTRS,
  },
  [ClusterTypes.TENDBHA]: {
    searchAttrs: TENDBHA_ATTRS,
  },
  [ClusterTypes.TENDBSINGLE]: {
    searchAttrs: TENDBHA_ATTRS,
  },
  tendbclusterSlave: {
    searchAttrs: TENDBCLUSTER_ATTRS,
    searchClusterType: ClusterTypes.TENDBCLUSTER,
  },
  /**
   * cluster-authorize/components/TargetInstances.vue 覆写了本 tab 的 getResourceList：
   * 它遍历 cluster_entry 的 slave_entry，把同一集群的每个从域名拆成一行（只有 master_domain 不同、
   * 共用一个集群 id），只用 id 做选中标识会互相串选，所以改用逐行唯一的从域名。
   * 前提是从域名非空——默认的 getTendbhaSalveList 是一行一集群，master_domain 取自 slave_domain。
   */
  tendbhaSlave: {
    rowKey: 'master_domain',
    searchAttrs: TENDBHA_ATTRS,
    searchClusterType: ClusterTypes.TENDBHA,
  },
};

/**
 * 行的唯一标识字段。表格勾选与右侧结果预览的增删必须取同一个，否则一 id 多行的 tab 会误删同组的其它行
 */
export const getTabRowKey = (tabId: string) => tableConfigMap[tabId]?.rowKey ?? 'id';
