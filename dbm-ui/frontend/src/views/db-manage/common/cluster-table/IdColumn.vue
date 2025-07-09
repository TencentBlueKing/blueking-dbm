<template>
  <TableColumn
    col-key="id"
    fixed="left"
    title="ID"
    :width="80" />
</template>
<script setup lang="ts">
  import type { ISupportClusterType } from './types';

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
  }

  defineProps<Props>();
</script>
