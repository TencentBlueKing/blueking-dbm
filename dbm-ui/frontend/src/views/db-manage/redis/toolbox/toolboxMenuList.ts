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

import { TicketTypes } from '@common/const';

import type { ToolboxTreeNode } from '@views/db-manage/common/toolbox-new/common/types';

import { t } from '@locales/index';

export const toolboxMenuList: ToolboxTreeNode[] = [
  {
    children: [
      {
        bind: [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE],
        dbConsoleValue: 'redis.toolbox.keyExtract',
        desc: t('提取或删除 Key'),
        id: TicketTypes.REDIS_KEYS_EXTRACT,
        name: t('Key 操作'),
      },
      {
        dbConsoleValue: 'redis.toolbox.webconsole',
        desc: t('连接集群执行只读指令'),
        id: 'RedisWebconsole',
        name: 'Webconsole',
      },
      {
        dbConsoleValue: 'redis.toolbox.queryAccessSource',
        desc: t('查看 Key 客户端来源'),
        id: 'RedisQueryAccessSource',
        name: t('查询访问来源'),
      },
    ],
    icon: 'chaxunyubiangeng',
    id: 'data-query',
    name: t('数据查询'),
  },
  {
    children: [
      {
        dbConsoleValue: 'redis.toolbox.memoryAnalysis',
        desc: t('分析内存占用'),
        id: TicketTypes.REDIS_KEYSTAT,
        name: t('内存分析'),
      },
      {
        dbConsoleValue: 'redis.toolbox.memoryAnalysisList',
        desc: t('查看内存分析结果'),
        id: 'RedisMemoryAnalysisList',
        name: t('内存分析报告'),
      },
      {
        dbConsoleValue: 'redis.toolbox.hotKeyAnalysis',
        desc: t('分析热 Key'),
        id: TicketTypes.REDIS_HOT_KEY_ANALYSIS,
        name: t('热 Key 分析'),
      },
      {
        dbConsoleValue: 'redis.toolbox.hotKeyAnalysisList',
        desc: t('查看热Key分析结果'),
        id: 'RedisHotKeyAnalysisList',
        name: t('热 Key 分析报告'),
      },
    ],
    icon: 'shujujiance',
    id: 'analyse',
    name: t('诊断分析'),
  },
  {
    children: [
      {
        dbConsoleValue: 'redis.toolbox.backup',
        desc: t('备份集群数据'),
        id: TicketTypes.REDIS_BACKUP,
        name: t('备份'),
      },
      {
        dbConsoleValue: 'redis.toolbox.purge',
        desc: t('清空所有数据'),
        id: TicketTypes.REDIS_PURGE,
        name: t('清档'),
      },
    ],
    icon: 'baofen',
    id: 'backup-and-purge',
    name: t('备份与清档'),
  },
  {
    children: [
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.proxyScaleUp',
            desc: t('增加 Proxy 节点'),
            id: TicketTypes.REDIS_PROXY_SCALE_UP,
            name: t('扩容接入层'),
          },
          {
            dbConsoleValue: 'redis.toolbox.proxyScaleDown',
            desc: t('减少 Proxy 节点'),
            id: TicketTypes.REDIS_PROXY_SCALE_DOWN,
            name: t('缩容接入层'),
          },
          {
            bind: [TicketTypes.REDIS_PROXY_KICKOFF, TicketTypes.REDIS_PROXY_FIX],
            dbConsoleValue: 'redis.toolbox.proxyKickoff',
            desc: t('剔除并修复异常 Proxy'),
            id: TicketTypes.REDIS_PROXY_KICKOFF,
            isFix: true,
            name: t('Proxy 剔除和修复'),
          },
        ],
        icon: '',
        id: 'proxy',
        name: t('接入层'),
      },
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.capacityChange',
            desc: t('调整规格或容量'),
            id: TicketTypes.REDIS_SCALE_UPDOWN,
            name: t('集群容量变更'),
          },
          {
            dbConsoleValue: 'redis.toolbox.clusterShardChange',
            desc: t('增减分片数'),
            id: TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE,
            name: t('集群分片变更'),
          },
          {
            bind: [TicketTypes.REDIS_SHARD_ADD, TicketTypes.REDIS_SHARD_REDUCE],
            dbConsoleValue: 'redis.toolbox.shardAdd',
            desc: t('通过增减分片数来搬迁Slot'),
            id: TicketTypes.REDIS_SHARD_ADD,
            name: t('集群分片变更（Slot 迁移）'),
          },
          {
            dbConsoleValue: 'redis.toolbox.clusterTypeChange',
            desc: t('变更集群架构'),
            id: TicketTypes.REDIS_CLUSTER_TYPE_UPDATE,
            name: t('集群类型变更'),
          },
        ],
        icon: '',
        id: 'cluster',
        name: t('集群变更'),
      },
    ],
    icon: 'cluster',
    id: 'cluster-manage',
    name: t('集群维护'),
  },
  {
    children: [
      {
        dbConsoleValue: 'redis.toolbox.dbReplace',
        desc: t('替换故障主机'),
        id: TicketTypes.REDIS_CLUSTER_CUTOFF,
        name: t('整机替换'),
      },
      {
        bind: [TicketTypes.REDIS_CLUSTER_INS_MIGRATE, TicketTypes.REDIS_SINGLE_INS_MIGRATE],
        dbConsoleValue: 'redis.toolbox.migrate',
        desc: t('实例迁移到新主机'),
        id: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
        name: t('迁移'),
      },
      {
        dbConsoleValue: 'redis.toolbox.masterSlaveSwap',
        desc: t('切换主从角色'),
        id: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
        isFix: true,
        name: t('主从切换'),
      },
      {
        dbConsoleValue: 'redis.toolbox.versionUpgrade',
        desc: t('升级集群版本'),
        id: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
        name: t('版本升级'),
      },
      {
        dbConsoleValue: 'redis.toolbox.installModule',
        desc: t('安装 Redis Module'),
        id: TicketTypes.REDIS_CLUSTER_LOAD_MODULES,
        name: t('安装 Module'),
      },
      {
        dbConsoleValue: 'redis.toolbox.clusterReinstallDbmon',
        desc: t('标准化集群配置和周边工具'),
        id: TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON,
        name: t('集群标准化'),
      },
      {
        dbConsoleValue: 'redis.toolbox.slaveRebuild',
        desc: t('原地或新机重建'),
        id: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
        isFix: true,
        name: t('重建从库'),
      },
    ],
    icon: 'resource',
    id: 'common',
    name: t('通用'),
  },
  {
    children: [
      {
        dbConsoleValue: 'redis.toolbox.rollbackRecord',
        desc: t('恢复数据到新集群'),
        id: 'RedisStructureInstance',
        name: t('构造实例'),
      },
      {
        dbConsoleValue: 'redis.toolbox.rollback',
        desc: t('恢复到指定时间点'),
        id: TicketTypes.REDIS_DATA_STRUCTURE,
        name: t('定点构造'),
      },
      {
        dbConsoleValue: 'redis.toolbox.recoverFromInstance',
        desc: t('写回目标集群'),
        id: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
        name: t('以构造实例恢复'),
      },
    ],
    icon: 'data-recovery',
    id: 'data-recovery',
    name: t('数据恢复'),
  },
  {
    children: [
      {
        dbConsoleValue: 'redis.toolbox.dataCopy',
        desc: t('在集群间同步数据'),
        id: TicketTypes.REDIS_CLUSTER_DATA_COPY,
        name: t('数据复制'),
      },
      {
        dbConsoleValue: 'redis.toolbox.dataCopyRecord',
        desc: t('查看任务记录'),
        id: 'RedisDBDataCopyRecord',
        name: t('数据复制记录'),
      },
    ],
    icon: 'migration',
    id: 'data-transfer',
    name: t('数据传输'),
  },
];
