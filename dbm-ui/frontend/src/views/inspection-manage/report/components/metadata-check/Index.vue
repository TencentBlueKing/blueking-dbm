<template>
  <RenderDynamicTable
    :service="getMetaCheckInsganceBelong"
    v-bind="attrs" />
</template>
<script setup lang="tsx">
  import { useAttrs } from 'vue';

  import { getMetaCheckInsganceBelong } from '@services/report';

  import RenderDynamicTable from '../RenderDynamicTable.vue';

  const attrs = useAttrs();
</script>

