<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getDbmonHeartbeat" />
</template>
<script setup lang="tsx">
  import {
    getDbmonHeartbeat,
  } from '@services/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();
</script>
