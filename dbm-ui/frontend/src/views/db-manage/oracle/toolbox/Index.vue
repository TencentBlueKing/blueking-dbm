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
          dbConsoleValue: 'oracle.toolbox.sqlExecute',
          id: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
          name: t('变更SQL执行'),
          parentId: 'sql',
        },
      ],
      icon: 'db-icon-mysql',
      id: 'sql',
      name: t('SQL任务'),
    },
  ];
</script>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';
</script>
