<template>
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getMetaCheckInsganceBelong" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getRedisMetaCheckAloneInstance" />
  <RenderDynamicTable
    :search-params="searchParams"
    :service="getRedisMetaCheckStatusAbnormal" />
</template>
<script setup lang="tsx">
  import {
    getMetaCheckInsganceBelong,
    getRedisMetaCheckAloneInstance,
    getRedisMetaCheckStatusAbnormal,
  } from '@services/report';

  import RenderDynamicTable from '../render-dynamic-table/Index.vue';

  interface Props {
    searchParams: Record<string, any>
  }

  defineProps<Props>();
</script>

