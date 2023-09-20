<template>
  <RenderDynamicTable
    :service="getReport"
    v-bind="attrs" />
  <RenderDynamicTable
    :service="getReport"
    v-bind="attrs" />
</template>
<script setup lang="tsx">
  import { useAttrs } from 'vue';

  import { getReport } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  const attrs = useAttrs();

</script>

