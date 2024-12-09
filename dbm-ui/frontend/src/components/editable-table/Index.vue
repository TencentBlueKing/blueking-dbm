<template>
  <div class="bk-editable-table">
    <div
      ref="tableRef"
      class="bk-editable-table-wrapper"
      @scroll="handleContentScroll">
      <table>
        <RenderHeader
          :column-list="columnList"
          :column-size-config="columnSizeConfig"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove" />
        <tbody class="bk-editable-table-body">
          <slot />
        </tbody>
      </table>
    </div>
    <div class="bk-editable-table-fixed-wrapper">
      <div
        class="bk-editable-table-fixed-left"
        :style="leftFixedStyles" />
      <div
        class="bk-editable-table-fixed-right"
        :style="rightFixedStyles" />
    </div>
    <div
      ref="resizePlaceholderRef"
      class="bk-editable-column-resize" />

    <div class="bk-edit-table-scroll">
      <div
        ref="scrollX"
        class="bk-edit-table-scroll-x"
        @scroll="handleScrollX">
        <div
          class="bk-edit-table-scroll-x-inner"
          :style="{
            width: tableWidth === 'auto' ? 'auto' : `${tableWidth}px`,
          }">
          &nbsp;
        </div>
        &nbsp;
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  import _ from 'lodash';
  import { type ComponentInternalInstance, type InjectionKey, provide, ref, shallowRef, type VNode, watch } from 'vue';

  import Column, { type IContext as IColumnContext } from './Column.vue';
  import RenderHeader from './component/render-header/Index.vue';
  import DatePicker from './edit/DatePicker.vue';
  import Input from './edit/Input.vue';
  import Select from './edit/Select.vue';
  import TagInput from './edit/TagInput.vue';
  import Text from './edit/Text.vue';
  import Textarea from './edit/Textarea.vue';
  import TimePicker from './edit/TimePicker.vue';
  import useResize from './hooks/use-resize';
  import useScroll from './hooks/use-scroll';
  import Row from './Row.vue';
  import { type IRule } from './types';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    model: Record<string, any>[];
    rules?: Record<string, IRule[]>;
  }

  interface Emits {
    (e: 'validate', property: string, result: boolean, message: string): boolean;
  }

  interface Slots {
    default: () => VNode;
  }

  interface Expose {
    validate: () => Promise<boolean>;
    validateByRowIndex: (row: number | number[]) => Promise<boolean>;
    validateByColumnIndex: (row: number | number[]) => Promise<boolean>;
    validateByField: (row: string | string[]) => Promise<boolean>;
  }

  export const tableInjectKey: InjectionKey<{
    props: Props;
    emits: Emits;
    registerRow: (rowColumnList: IColumnContext[]) => void;
    updateRow: () => void;
    unregisterRow: (rowColumnList: IColumnContext[]) => void;
    getAllColumnList: () => IColumnContext[][];
    getColumnRelateRowIndexByInstance: (columnInstance: ComponentInternalInstance) => number;
  }> = Symbol.for('bk-editable-table');

  export { Column, DatePicker, Input, Row, Select, TagInput, Text, Textarea, TimePicker };
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineSlots<Slots>();

  defineOptions({
    name: 'EditableTable',
  });

  const tableRef = ref<HTMLElement>();
  const scrollX = ref<HTMLElement>();
  const resizePlaceholderRef = ref<HTMLElement>();
  const tableWidth = ref<'auto' | number>('auto');

  const columnList = shallowRef<IColumnContext[]>([]);
  const rowList = shallowRef<IColumnContext[][]>([]);

  const { handleMouseDown, handleMouseMove, columnSizeConfig } = useResize(tableRef, resizePlaceholderRef, columnList);
  const { leftFixedStyles, rightFixedStyles, initalScroll } = useScroll(tableRef);

  watch(columnList, () => {
    initalScroll();
  });

  watch(
    columnSizeConfig,
    () => {
      nextTick(() => {
        if (!tableRef.value) {
          return;
        }
        tableWidth.value = tableRef.value.scrollWidth;
        scrollX.value!.scrollLeft = tableRef.value!.scrollLeft;
      });
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const registerRow = (rowColumnList: IColumnContext[]) => {
    rowList.value.push(rowColumnList);
  };

  const updateRow = _.throttle(() => {
    columnList.value = rowList.value.length > 0 ? [...rowList.value[0]] : [];
  }, 60);

  const unregisterRow = (rowColumnList: IColumnContext[]) => {
    rowList.value = rowList.value.filter((row) => row !== rowColumnList);
  };

  const getColumnRelateRowIndexByInstance = (columnInstance: ComponentInternalInstance) =>
    _.findIndex(rowList.value, (rowColumnList) =>
      _.some(rowColumnList, (column) => column.instance === columnInstance),
    );

  provide(tableInjectKey, {
    props,
    emits,
    registerRow,
    updateRow,
    unregisterRow,
    getAllColumnList: () => rowList.value,
    getColumnRelateRowIndexByInstance,
  });

  const handleScrollX = _.throttle((event: Event) => {
    tableRef.value!.scrollLeft = (event.target as Element)!.scrollLeft;
  }, 30);

  const handleContentScroll = _.throttle((event: Event) => {
    scrollX.value!.scrollLeft = (event.target as Element)!.scrollLeft;
    tableRef.value?.click();
  }, 30);

  defineExpose<Expose>({
    validate() {
      return Promise.all(_.flatten(rowList.value).map((column) => column.validate())).then(
        () => true,
        () => false,
      );
    },
    validateByRowIndex(rowIndex: number | number[]) {
      const rowIndexList = Array.isArray(rowIndex) ? rowIndex : [rowIndex];

      const columnList = rowIndexList.reduce<IColumnContext[]>((result, index) => {
        result.push(...rowList.value[index]);
        return result;
      }, []);

      return Promise.all(columnList.map((column) => column.validate())).then(
        () => true,
        () => false,
      );
    },
    validateByColumnIndex(columnIndex: number | number[]) {
      const columnIndexList = Array.isArray(columnIndex) ? columnIndex : [columnIndex];

      const columnList = rowList.value.reduce((result, rowItem) => {
        columnIndexList.forEach((index) => {
          result.push(rowItem[index]);
        });
        return result;
      }, []);

      return Promise.all(columnList.map((column) => column.validate())).then(
        () => true,
        () => false,
      );
    },
    validateByField(field: string | string[]) {
      const fieldList = Array.isArray(field) ? field : [field];

      const columnList = rowList.value.reduce((result, rowItem) => {
        fieldList.forEach((field) => {
          rowItem.forEach((column) => {
            if (column.props.field && column.props.field === field) {
              result.push(column);
            }
          });
        });
        return result;
      }, []);

      return Promise.all(columnList.map((column) => column.validate())).then(
        () => true,
        () => false,
      );
    },
  });
</script>
<style lang="less">
  .bk-editable-table {
    position: relative;
    background: #fff;
    transform: translate3d(0);

    &::before {
      position: absolute;
      z-index: 9;
      pointer-events: none;
      border-right: 1px solid #dcdee5;
      border-left: 1px solid #dcdee5;
      content: '';
      inset: 0;
    }

    .bk-editable-table-wrapper {
      overflow: scroll hidden;

      &::-webkit-scrollbar {
        width: 0;
        height: 0;
      }
    }

    table {
      width: 100%;
      text-align: left;
      table-layout: fixed;
    }

    tbody {
      tr {
        td {
          &::before {
            top: -1px;
          }
        }
      }
    }

    th,
    td {
      position: relative;
      z-index: 0;
      font-size: 12px;
      font-weight: normal;

      &::before {
        position: absolute;
        z-index: 99999;
        pointer-events: none;
        border: 1px solid #dcdee5;
        content: '';
        inset: 0;
      }

      &:nth-child(n + 2) {
        &::before {
          left: -1px;
        }
      }

      &.is-column-fixed-left {
        position: sticky;
        left: 0;
        z-index: 9;
        background: #fff;
      }

      &.is-column-fixed-right {
        position: sticky;
        right: 0;
        background: #fff;
      }
    }

    th {
      padding: 0 10px;
      color: #313238;
      background-color: #fafbfd;

      &.is-column-fixed-left,
      &.is-column-fixed-right {
        background-color: #fafbfd;
      }

      &:hover {
        background-color: #f0f1f5;
      }
    }

    td {
      padding: 0;

      &.is-column-fixed-left,
      &.is-column-fixed-right {
        background: #fff;
      }
    }

    &:hover {
      .bk-edit-table-scroll-x {
        opacity: 100%;
      }
    }
  }

  .bk-editable-table-fixed-wrapper {
    position: absolute;
    overflow: hidden;
    pointer-events: none;
    inset: 0;
  }

  .bk-editable-table-fixed-left {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    overflow-x: hidden;
    pointer-events: none;
    box-shadow: 8px 0 10px -5px rgb(0 0 0 / 12%);
  }

  .bk-editable-table-fixed-right {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    box-shadow: 8px 0 10px -5px rgb(0 0 0 / 12%);
  }

  .bk-editable-column-resize {
    position: absolute;
    top: 0;
    bottom: 0;
    display: none;
    width: 1px;
    background: #dfe0e5;
  }

  .bk-edit-table-scroll-x {
    position: absolute;
    right: 1px;
    bottom: 0;
    left: 1px;
    z-index: 99999999;
    height: 14px;
    overflow: scroll hidden;
    cursor: pointer;
    opacity: 0%;
    transition: 0.15s;

    &::-webkit-scrollbar {
      height: 6px;
      transition: 0.15s;
    }

    &::-webkit-scrollbar-thumb {
      background-color: rgb(151 155 165 / 80%);
      border-radius: 3px;
    }

    &:hover {
      &::-webkit-scrollbar {
        height: 14px;
      }

      &::-webkit-scrollbar-thumb {
        background-color: rgb(151 155 165 / 90%);
        border-radius: 7px;
      }
    }
  }
</style>
