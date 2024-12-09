<template>
  <colgroup>
    <col
      v-for="item in columnList"
      :key="item.key"
      :width="columnSizeMap[item.key].renderWidth ? columnSizeMap[item.key].renderWidth : ''" />
  </colgroup>
</template>
<script setup lang="ts">
  import type { IContext as IColumnContext } from '../Column.vue';

  interface Props {
    columnList: IColumnContext[];
    columnSizeMap: Record<
      string,
      {
        width?: number;
        minWidth?: number;
        maxWidth?: number;
        renderWidth: number;
      }
    >;
  }

  defineProps<Props>();
</script>
