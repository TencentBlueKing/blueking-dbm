<template>
  <tbody>
    <tr>
      <RenderCell
        v-for="(columnItem, index) in columnList"
        :key="`#${index}}#${columnItem.props.field}`"
        :column="columnItem" />
    </tr>
  </tbody>
</template>
<script setup lang="ts">
  import type { IContext as IColumnContext } from '../../Column.vue';

  import RenderCell from './render-cell';

  interface Props {
    columnList: IColumnContext[];
  }

  defineProps<Props>();
</script>
<style lang="less">
  .bk-editable-table-cell {
    display: flex;
    min-height: 40px;
    align-items: center;
  }
</style>
