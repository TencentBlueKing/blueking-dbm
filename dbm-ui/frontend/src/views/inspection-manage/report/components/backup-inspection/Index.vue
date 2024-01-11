<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getmysqlCheckFullBackup" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getmysqlCheckBinlogBackup" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getRedisCheckFullBackup" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getRedisCheckBinlogBackup" />
</template>
<script setup lang="tsx">
  import {
    getmysqlCheckBinlogBackup,
    getmysqlCheckFullBackup,
    getRedisCheckBinlogBackup,
    getRedisCheckFullBackup,
  } from '@services/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();

</script>

