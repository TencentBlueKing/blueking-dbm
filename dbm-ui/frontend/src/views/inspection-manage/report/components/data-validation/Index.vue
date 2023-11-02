<template>
  <RenderDynamicTable
    :service="getChecksumReport"
    v-bind="attrs" />
  <RenderDynamicTable
    :service="getChecksumInstance"
    v-bind="attrs" />
</template>
<script setup lang="tsx">
  import { useAttrs } from 'vue';

  import {
    getChecksumInstance,
    getChecksumReport,
  } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  const attrs = useAttrs();

</script>

