<template>
  <ToolBox :menu-list="toolboxMenuList" />
</template>
<script lang="ts">
  import { TicketTypes } from '@common/const';

  import { t } from '@locales/index';

  export const toolboxMenuList = [
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.scriptExecute',
          id: TicketTypes.MONGODB_EXEC_SCRIPT_APPLY,
          name: t('变更脚本执行'),
          parentId: 'mongo_script',
        },
      ],
      icon: 'db-icon-mysql',
      id: 'mongo_script',
      name: t('脚本任务'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.addShard',
          id: TicketTypes.MONGODB_ADD_SHARD,
          name: t('分片集群增加分片数'),
          parentId: 'mongo_manage',
        },
        {
          bind: [TicketTypes.MONGODB_REPLICA_ADD_SHARD_NODES, TicketTypes.MONGODB_SHARD_ADD_SHARD_NODES],
          dbConsoleValue: 'mongodb.toolbox.shardScaleUp',
          id: TicketTypes.MONGODB_REPLICA_ADD_SHARD_NODES,
          name: t('扩容Shard节点数'),
          parentId: 'mongo_manage',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.shardScaleDown',
          id: TicketTypes.MONGODB_REDUCE_SHARD_NODES,
          name: t('缩容Shard节点数'),
          parentId: 'mongo_manage',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.scaleUpDown',
          id: TicketTypes.MONGODB_SCALE_UPDOWN,
          name: t('集群容量变更'),
          parentId: 'mongo_manage',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.proxyScaleUp',
          id: TicketTypes.MONGODB_ADD_MONGOS,
          name: t('扩容接入层'),
          parentId: 'mongo_manage',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.reduceMongos',
          id: TicketTypes.MONGODB_REDUCE_MONGOS,
          name: t('缩容接入层'),
          parentId: 'mongo_manage',
        },
        {
          bind: [TicketTypes.MONGODB_REPLICASET_CUTOFF, TicketTypes.MONGODB_SHARD_CUTOFF],
          dbConsoleValue: 'mongodb.toolbox.cutoff',
          id: TicketTypes.MONGODB_REPLICASET_CUTOFF,
          name: t('整机替换'),
          parentId: 'mongo_manage',
        },
        {
          bind: [TicketTypes.MONGODB_REPLICASET_MIGRATE, TicketTypes.MONGODB_SHARD_MIGRATE],
          dbConsoleValue: 'mongodb.toolbox.replicasetMigrate',
          id: TicketTypes.MONGODB_REPLICASET_MIGRATE,
          name: t('迁移'),
          parentId: 'mongo_manage',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.instanceFixStatus',
          id: TicketTypes.MONGODB_INSTANCE_FIX_STATUS,
          name: t('节点状态修复'),
          parentId: 'mongo_data',
        },
      ],
      icon: 'db-icon-cluster',
      id: 'mongo_manage',
      name: t('集群维护'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.pitrRestore',
          id: TicketTypes.MONGODB_PITR_RESTORE,
          name: t('定点构造'),
          parentId: 'mongo_rollback',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.structureInstance',
          id: 'MongoStructureInstance',
          name: t('构造实例'),
          parentId: 'mongo_rollback',
        },
      ],
      icon: 'db-icon-copy',
      id: 'mongo_rollback',
      name: t('回档'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.dbTableBackup',
          id: TicketTypes.MONGODB_BACKUP,
          name: t('库表备份'),
          parentId: 'mongo_backup',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.dbBackup',
          id: TicketTypes.MONGODB_FULL_BACKUP,
          name: t('全库备份'),
          parentId: 'mongo_backup',
        },
      ],
      icon: 'db-icon-copy',
      id: 'mongo_backup',
      name: t('备份'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.dbClear',
          id: TicketTypes.MONGODB_REMOVE_NS,
          name: t('清档'),
          parentId: 'mongo_data',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.dataExport',
          id: TicketTypes.MONGODB_DATA_EXPORT,
          name: t('数据导出'),
          parentId: 'mongo_data',
        },
      ],
      icon: 'db-icon-data',
      id: 'mongo_data',
      name: t('数据处理'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mongodb.toolbox.queryAccessSource',
          id: 'MongodbQueryAccessSource',
          name: t('查询访问来源'),
          parentId: 'mongo_data_query',
        },
        {
          dbConsoleValue: 'mongodb.toolbox.webconsole',
          id: 'MongodbWebconsole',
          name: 'Webconsole',
          parentId: 'mongo_data_query',
        },
      ],
      icon: 'db-icon-search',
      id: 'mongo_data_query',
      name: t('常用查询'),
    },
  ];
</script>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';
</script>
