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
  } from '@services/source/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();

</script>

