<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getmysqlCheckFullBackup" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getmysqlCheckBinlogBackup" />
</template>
<script setup lang="tsx">
  import {
    getmysqlCheckBinlogBackup,
    getmysqlCheckFullBackup,
  } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();

</script>

