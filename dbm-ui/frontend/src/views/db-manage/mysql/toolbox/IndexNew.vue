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
          dbConsoleValue: 'mysql.toolbox.sqlExecute',
          id: TicketTypes.MYSQL_IMPORT_SQLFILE,
          name: t('变更SQL执行'),
          parentId: 'sql',
        },
        {
          dbConsoleValue: 'mysql.toolbox.dbRename',
          id: TicketTypes.MYSQL_RENAME_DATABASE,
          name: t('DB重命名'),
          parentId: 'sql',
        },
      ],
      icon: 'db-icon-mysql',
      id: 'sql',
      name: t('SQL任务'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mysql.toolbox.dbTableBackup',
          id: TicketTypes.MYSQL_HA_DB_TABLE_BACKUP,
          name: t('库表备份'),
          parentId: 'copy',
        },
        {
          dbConsoleValue: 'mysql.toolbox.dbBackup',
          id: TicketTypes.MYSQL_HA_FULL_BACKUP,
          name: t('全库备份'),
          parentId: 'copy',
        },
      ],
      icon: 'db-icon-copy',
      id: 'copy',
      name: t('备份'),
    },
    {
      children: [
        {
          bind: [TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER, TicketTypes.MYSQL_FIXPOINT_NEW_CLUSTER],
          dbConsoleValue: 'mysql.toolbox.fixpoint',
          id: TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER,
          name: t('构造'),
          parentId: 'fileback',
        },
        {
          bind: [TicketTypes.MYSQL_FLASHBACK, TicketTypes.MYSQL_ROLLBACK],
          dbConsoleValue: 'mysql.toolbox.flashback',
          id: TicketTypes.MYSQL_ROLLBACK,
          name: t('回档'),
          parentId: 'fileback',
        },
        {
          dbConsoleValue: 'mysql.toolbox.rollback',
          id: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
          name: t('定点构造（旧）'),
          parentId: 'fileback',
        },
      ],
      icon: 'db-icon-rollback',
      id: 'fileback',
      name: t('构造和回档'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mysql.toolbox.clientPermissionClone',
          id: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
          name: t('客户端权限克隆'),
          parentId: 'privilege',
        },
        {
          dbConsoleValue: 'mysql.toolbox.dbInstancePermissionClone',
          id: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
          name: t('DB实例权限克隆'),
          parentId: 'privilege',
        },
      ],
      icon: 'db-icon-clone',
      id: 'privilege',
      name: t('权限克隆'),
    },
    {
      children: [
        {
          bind: [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, TicketTypes.MYSQL_RESTORE_SLAVE],
          dbConsoleValue: 'mysql.toolbox.slaveRebuild',
          id: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
          name: t('重建从库'),
          parentId: 'migrate',
        },
        {
          dbConsoleValue: 'mysql.toolbox.slaveAdd',
          id: TicketTypes.MYSQL_ADD_SLAVE,
          name: t('添加从库'),
          parentId: 'migrate',
        },
        {
          dbConsoleValue: 'mysql.toolbox.masterSlaveClone',
          id: TicketTypes.MYSQL_MIGRATE_CLUSTER,
          name: t('迁移主从'),
          parentId: 'migrate',
        },
        {
          dbConsoleValue: 'mysql.toolbox.masterSlaveSwap',
          id: TicketTypes.MYSQL_MASTER_SLAVE_SWITCH,
          name: t('主从互切'),
          parentId: 'migrate',
        },
        {
          bind: [
            TicketTypes.MYSQL_PROXY_ADD,
            TicketTypes.MYSQL_PROXY_REDUCE,
            TicketTypes.MYSQL_PROXY_SWITCH,
            TicketTypes.MYSQL_PROXY_CONF_CHANGE,
            TicketTypes.MYSQL_PROXY_MIGRATE,
            TicketTypes.MYSQL_PROXY_MIGRATE_INS,
          ],
          dbConsoleValue: 'mysql.toolbox.proxyAdd',
          id: TicketTypes.MYSQL_PROXY_ADD,
          name: t('接入层变更'),
          parentId: 'migrate',
        },
        {
          bind: [TicketTypes.MYSQL_MASTER_FAIL_OVER, TicketTypes.MYSQL_INSTANCE_FAIL_OVER],
          dbConsoleValue: 'mysql.toolbox.instanceFailover',
          id: TicketTypes.MYSQL_MASTER_FAIL_OVER,
          name: t('主库故障切换'),
          parentId: 'migrate',
        },
        {
          bind: [TicketTypes.MYSQL_LOCAL_UPGRADE, TicketTypes.MYSQL_MIGRATE_UPGRADE, TicketTypes.MYSQL_PROXY_UPGRADE],
          dbConsoleValue: 'mysql.toolbox.versionUpgrade',
          id: TicketTypes.MYSQL_PROXY_UPGRADE,
          name: t('版本升级'),
          parentId: 'migrate',
        },
        {
          dbConsoleValue: 'mysql.toolbox.migrateSingle',
          id: TicketTypes.MYSQL_MIGRATE_SINGLE,
          name: t('单节点迁移'),
          parentId: 'migrate',
        },
        {
          dbConsoleValue: 'mysql.toolbox.clusterStandardize',
          id: TicketTypes.MYSQL_CLUSTER_STANDARDIZE,
          name: t('集群标准化'),
          parentId: 'migrate',
        },
      ],
      icon: 'db-icon-cluster',
      id: 'migrate',
      name: t('集群维护'),
    },
    {
      children: [
        {
          bind: [TicketTypes.MYSQL_HA_TRUNCATE_DATA, TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA],
          dbConsoleValue: 'mysql.toolbox.dbClear',
          id: TicketTypes.MYSQL_HA_TRUNCATE_DATA,
          name: t('清档'),
          parentId: 'data',
        },
        {
          dbConsoleValue: 'mysql.toolbox.checksum',
          id: TicketTypes.MYSQL_CHECKSUM,
          name: t('数据校验修复'),
          parentId: 'data',
        },
        {
          dbConsoleValue: 'mysql.toolbox.dataMigrate',
          id: TicketTypes.MYSQL_DATA_MIGRATE,
          name: t('DB 数据克隆'),
          parentId: 'data',
        },
        {
          dbConsoleValue: 'mysql.toolbox.mergeDiskSpace',
          id: 'MySQLMergeDiskSpace',
          name: t('DB 数据合并空间评估'),
          parentId: 'data',
        },
      ],
      icon: 'db-icon-data',
      id: 'data',
      name: t('数据处理'),
    },
    {
      children: [
        // {
        //   dbConsoleValue: 'mysql.toolbox.openareaTemplate',
        //   id: 'MySQLOpenareaTemplate',
        //   name: t('开区模版'),
        //   parentId: 'mysql_openarea',
        // },
        {
          dbConsoleValue: 'mysql.toolbox.openareaTemplate',
          id: TicketTypes.MYSQL_OPEN_AREA,
          name: t('开区模版'),
          parentId: 'mysql_openarea',
        },
      ],
      icon: 'db-icon-template',
      id: 'mysql_openarea',
      name: t('克隆开区'),
    },
    {
      children: [
        {
          dbConsoleValue: 'mysql.toolbox.webconsole',
          id: 'MySQLWebconsole',
          name: 'Webconsole',
          parentId: 'mysql_data_query',
        },
      ],
      icon: 'db-icon-search',
      id: 'mysql_data_query',
      name: t('数据查询'),
    },
  ];
</script>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';
</script>
