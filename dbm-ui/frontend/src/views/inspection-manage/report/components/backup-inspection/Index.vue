<template>
  <RenderDynamicTable
    :service="getmysqlCheckFullBackup"
    v-bind="attrs" />
  <RenderDynamicTable
    :service="getmysqlCheckBinlogBackup"
    v-bind="attrs" />
</template>
<script setup lang="tsx">
  import { useAttrs } from 'vue';

  import {
    getmysqlCheckBinlogBackup,
    getmysqlCheckFullBackup,
  } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  const attrs = useAttrs();

</script>

