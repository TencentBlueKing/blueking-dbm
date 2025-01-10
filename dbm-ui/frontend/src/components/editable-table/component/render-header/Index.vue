<template>
  <thead class="bk-editable-table-header">
    <tr>
      <RenderTh
        v-for="(columnItem, index) in columnList"
        :key="`#${index}}#${columnItem.key}`"
        :class="{
          'fixed-left-column': columnItem.props.fixed === 'left',
          'fixed-right-column': columnItem.props.fixed === 'right',
        }"
        :column="columnItem"
        :column-size-config="columnSizeConfig"
        :style="{
          width:
            columnSizeConfig[columnItem.key].renderWidth > 0 ? `${columnSizeConfig[columnItem.key].renderWidth}px` : '',
        }" />
    </tr>
  </thead>
</template>
<script setup lang="ts">
  import type { IContext as IColumnContext } from '../../Column.vue';

  import RenderTh from './render-th';

  interface Props {
    columnList: IColumnContext[];
    columnSizeConfig: Record<string, Record<'renderWidth', number>>;
  }

  defineProps<Props>();
</script>
<style lang="less">
  .bk-editable-table-header {
    th.is-required {
      .bk-editable-table-label-cell {
        &::after {
          margin-left: 4px;
          line-height: 20px;
          color: #ea3636;
          content: '*';
        }
      }
    }
  }

  .bk-editable-table-label-cell {
    display: flex;
    min-height: 40px;
    align-items: center;
    font-weight: normal;
    color: #313238;
  }

  .bk-editable-table-th-prepend {
    margin-right: 4px;
  }

  .bk-editable-table-th-text {
    display: flex;
    height: 20px;
    overflow: hidden;
    line-height: 20px;
    text-overflow: ellipsis;
    word-break: keep-all;
    white-space: nowrap;
  }

  .bk-editable-table-th-text-description {
    cursor: pointer;
    border-bottom: 1px dashed #979ba5;
  }

  .bk-editable-table-th-append {
    margin-left: 4px;
  }
</style>
