<template>
  <ToolBox
    :menu-group-list="menuGroupList"
    :menu-list="toolboxMenuList" />
</template>
<script lang="ts">
  import { TicketTypes } from '@common/const';

  import { t } from '@locales/index';

  export const toolboxMenuList = [
    {
      children: [
        {
          bind: [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE],
          dbConsoleValue: 'redis.toolbox.keyExtract',
          id: TicketTypes.REDIS_KEYS_EXTRACT,
          name: t('Key 操作'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.backup',
          id: TicketTypes.REDIS_BACKUP,
          name: t('备份'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.purge',
          id: TicketTypes.REDIS_PURGE,
          name: t('清档'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.slaveRebuild',
          id: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
          name: t('重建从库'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.masterSlaveSwap',
          id: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
          name: t('主从切换'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.dbReplace',
          id: TicketTypes.REDIS_CLUSTER_CUTOFF,
          name: t('整机替换'),
          parentId: 'common-manage',
        },
        {
          bind: [TicketTypes.REDIS_CLUSTER_INS_MIGRATE, TicketTypes.REDIS_SINGLE_INS_MIGRATE],
          dbConsoleValue: 'redis.toolbox.migrate',
          id: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
          name: t('迁移'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.versionUpgrade',
          id: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
          name: t('版本升级'),
          parentId: 'common-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.installModule',
          id: TicketTypes.REDIS_CLUSTER_LOAD_MODULES,
          name: t('安装 Module'),
          parentId: 'cluster-manage',
        },
        {
          dbConsoleValue: 'redis.toolbox.clusterReinstallDbmon',
          id: TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON,
          name: t('集群标准化'),
          parentId: 'cluster-manage',
        },
      ],
      icon: 'db-icon-cluster',
      id: 'common-manage',
      name: t('通用维护'),
    },
    {
      children: [
        {
          dbConsoleValue: 'redis.toolbox.rollback',
          id: TicketTypes.REDIS_DATA_STRUCTURE,
          name: t('定点构造'),
          parentId: 'common-struct',
        },
        {
          dbConsoleValue: 'redis.toolbox.rollbackRecord',
          id: 'RedisStructureInstance',
          name: t('构造实例'),
          parentId: 'common-struct',
        },
        {
          dbConsoleValue: 'redis.toolbox.recoverFromInstance',
          id: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
          name: t('以构造实例恢复'),
          parentId: 'common-struct',
        },
      ],
      icon: 'db-icon-copy',
      id: 'common-struct',
      name: t('数据构造'),
    },
    {
      children: [
        {
          dbConsoleValue: 'redis.toolbox.dataCopy',
          id: TicketTypes.REDIS_CLUSTER_DATA_COPY,
          name: t('数据复制'),
          parentId: 'common-dts',
        },
        {
          dbConsoleValue: 'redis.toolbox.dataCopyRecord',
          id: 'RedisDBDataCopyRecord',
          name: t('数据复制记录'),
          parentId: 'common-dts',
        },
      ],
      icon: 'db-icon-data',
      id: 'common-dts',
      name: t('数据传输（DTS）'),
    },
    {
      children: [
        {
          dbConsoleValue: 'redis.toolbox.memoryAnalysis',
          id: TicketTypes.REDIS_KEYSTAT,
          name: t('内存分析'),
          parentId: 'redis_data_query',
        },
        {
          dbConsoleValue: 'redis.toolbox.memoryAnalysisList',
          id: 'RedisMemoryAnalysisList',
          name: t('内存分析报告'),
          parentId: 'redis_data_query',
        },
        {
          dbConsoleValue: 'redis.toolbox.hotKeyAnalysis',
          id: TicketTypes.REDIS_HOT_KEY_ANALYSIS,
          name: t('热 Key 分析'),
          parentId: 'redis_data_query',
        },
        {
          dbConsoleValue: 'redis.toolbox.hotKeyAnalysisList',
          id: 'RedisHotKeyAnalysisList',
          name: t('热 Key 分析报告'),
          parentId: 'redis_data_query',
        },
      ],
      icon: 'db-icon-search',
      id: 'redis_analyse',
      name: t('分析'),
    },
    {
      children: [
        {
          dbConsoleValue: 'redis.toolbox.queryAccessSource',
          id: 'RedisQueryAccessSource',
          name: t('查询访问来源'),
          parentId: 'redis_data_query',
        },
        {
          dbConsoleValue: 'redis.toolbox.webconsole',
          id: 'RedisWebconsole',
          name: 'Webconsole',
          parentId: 'redis_data_query',
        },
      ],
      icon: 'db-icon-search',
      id: 'redis_data_query',
      name: t('数据查询'),
    },
  ];

  export const menuGroupList = [
    {
      description: t('支持所有架构类型'),
      id: 'common',
      menuList: ['common-manage', 'common-struct', 'common-dts', 'redis_analyse', 'redis_data_query'],
      name: t('通用维护'),
    },
    {
      description: t('仅支持 TendisCache，TendisSSD，Tendisplus，RedisCluster 类型'),
      id: 'cluster',
      menuList: ['cluster-manage'],
      name: t('集群'),
    },
  ];
</script>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';
</script>
