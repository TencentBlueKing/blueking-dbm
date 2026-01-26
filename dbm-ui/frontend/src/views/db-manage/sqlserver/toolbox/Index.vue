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
          id: TicketTypes.SQLSERVER_IMPORT_SQLFILE,
          name: t('变更SQL执行'),
        },
        {
          id: TicketTypes.SQLSERVER_DBRENAME,
          name: t('DB重命名'),
        },
      ],
      icon: 'db-icon-mysql',
      id: 'sql',
      name: t('SQL任务'),
    },
    {
      children: [
        {
          id: TicketTypes.SQLSERVER_BACKUP_DBS,
          name: t('库表备份'),
        },
      ],
      icon: 'db-icon-copy',
      id: 'copy',
      name: t('备份'),
    },
    {
      children: [
        {
          id: TicketTypes.SQLSERVER_ROLLBACK,
          name: t('定点构造'),
        },
      ],
      icon: 'db-icon-rollback',
      id: 'fileback',
      name: t('回档'),
    },
    {
      children: [
        {
          bind: [TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE, TicketTypes.SQLSERVER_RESTORE_SLAVE],
          id: TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE,
          name: t('重建从库'),
        },
        {
          id: TicketTypes.SQLSERVER_ADD_SLAVE,
          name: t('添加从库'),
        },
        {
          id: TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH,
          name: t('主从互切'),
        },
        {
          id: TicketTypes.SQLSERVER_MASTER_FAIL_OVER,
          name: t('主库故障切换'),
        },
        {
          bind: [TicketTypes.SQLSERVER_CLUSTER_MIGRATE, TicketTypes.SQLSERVER_HOST_MIGRATE],
          id: TicketTypes.SQLSERVER_CLUSTER_MIGRATE,
          name: t('迁移'),
        },
      ],
      icon: 'db-icon-cluster',
      id: 'migrate',
      name: t('集群维护'),
    },
    {
      children: [
        {
          id: TicketTypes.SQLSERVER_DATA_EXPORT,
          name: t('数据导出'),
          parentId: 'migrate',
        },
        {
          bind: [TicketTypes.SQLSERVER_FULL_MIGRATE, TicketTypes.SQLSERVER_INCR_MIGRATE],
          id: TicketTypes.SQLSERVER_FULL_MIGRATE,
          name: t('数据迁移'),
        },
        {
          id: 'sqlServerDataMigrateRecord',
          name: t('迁移记录'),
        },
        {
          id: TicketTypes.SQLSERVER_CLEAR_DBS,
          name: t('清档'),
        },
      ],
      icon: 'db-icon-data',
      id: 'data',
      name: t('数据处理'),
    },
  ];
</script>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';
</script>
