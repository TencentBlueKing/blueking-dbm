<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getChecksumReport" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getChecksumInstance" />
</template>
<script setup lang="tsx">

  import {
    getChecksumInstance,
    getChecksumReport,
  } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();

</script>

