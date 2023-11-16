<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getMetaCheckInsganceBelong" />
</template>
<script setup lang="tsx">

  import { getMetaCheckInsganceBelong } from '@services/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();
</script>

