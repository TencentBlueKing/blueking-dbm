<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getChecksumReport" />
</template>
<script setup lang="tsx">
  import { getChecksumReport } from '@services/source/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>;
  }

  defineProps<Props>();
</script>
