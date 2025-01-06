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
        ref="scrollXRef"
        class="bk-edit-table-scroll-x"
        :class="{
          'is-show': isShowScrollX,
        }"
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
  import {
    type ComponentInternalInstance,
    type InjectionKey,
    provide,
    type Ref,
    ref,
    shallowRef,
    type VNode,
    watch,
  } from 'vue';

  import Column, { type IContext as IColumnContext } from './Column.vue';
  import RenderHeader from './component/render-header/Index.vue';
  import Block from './edit/Block.vue';
  import DatePicker from './edit/DatePicker.vue';
  import Input from './edit/Input.vue';
  import Select from './edit/Select.vue';
  import TagInput from './edit/TagInput.vue';
  import Textarea from './edit/Textarea.vue';
  import TimePicker from './edit/TimePicker.vue';
  import useResize from './hooks/use-resize';
  import useScroll from './hooks/use-scroll';
  import Row from './Row.vue';
  import { type IRule } from './types';
  import useColumn from './useColumn';
  import useTable from './useTable';

  /* eslint-disable vue/no-unused-properties */
  export interface Props {
    model: Record<string, any>[];
    rules?: Record<string, IRule[]>;
    validateDelay?: number;
  }

  export type Emits = (e: 'validate', property: string, result: boolean, message: string) => boolean;

  export interface Slots {
    default: () => VNode;
  }

  export interface Expose {
    validate: () => Promise<boolean>;
    validateByRowIndex: (row: number | number[]) => Promise<boolean>;
    validateByColumnIndex: (row: number | number[]) => Promise<boolean>;
    validateByField: (row: string | string[]) => Promise<boolean>;
  }

  export const tableInjectKey: InjectionKey<
    {
      props: Props;
      emits: Emits;
      fixedRight: Ref<boolean>;
      fixedLeft: Ref<boolean>;
      columnSizeConfig: Ref<Record<string, { renderWidth: number }>>;
      registerRow: (rowColumnList: IColumnContext[]) => void;
      updateRow: () => void;
      unregisterRow: (rowColumnList: IColumnContext[]) => void;
      getAllColumnList: () => IColumnContext[][];
      getColumnRelateRowIndexByInstance: (columnInstance: ComponentInternalInstance) => number;
    } & Expose
  > = Symbol.for('bk-editable-table');

  export { Block, Column, DatePicker, Input, Row, Select, TagInput, Textarea, TimePicker, useColumn, useTable };
</script>
<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineSlots<Slots>();

  defineOptions({
    name: 'EditableTable',
  });

  const tableRef = ref<HTMLElement>();
  const scrollXRef = ref<HTMLElement>();
  const resizePlaceholderRef = ref<HTMLElement>();
  const tableWidth = ref<'auto' | number>('auto');

  const columnList = shallowRef<IColumnContext[]>([]);
  const rowList = shallowRef<IColumnContext[][]>([]);

  const isShowScrollX = ref(true);

  const { handleMouseDown, handleMouseMove, columnSizeConfig } = useResize(tableRef, resizePlaceholderRef, columnList);
  const { leftFixedStyles, rightFixedStyles, initalScroll, fixedLeft, fixedRight } = useScroll(tableRef);

  watch(
    columnSizeConfig,
    () => {
      nextTick(() => {
        if (!tableRef.value) {
          return;
        }
        tableWidth.value = tableRef.value.scrollWidth;
        scrollXRef.value!.scrollLeft = tableRef.value!.scrollLeft;
        // 重新计算滚动显示状态
        isShowScrollX.value = false;
        setTimeout(() => {
          isShowScrollX.value = scrollXRef.value!.offsetWidth + 2 < scrollXRef.value!.scrollWidth;
        });
        initalScroll();
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

  const handleScrollX = _.throttle((event: Event) => {
    tableRef.value!.scrollLeft = (event.target as Element)!.scrollLeft;
  }, 30);

  const handleContentScroll = _.throttle((event: Event) => {
    scrollXRef.value!.scrollLeft = (event.target as Element)!.scrollLeft;
    tableRef.value?.click();
  }, 30);

  const validate = () => Promise.all(_.flatten(rowList.value).map((column) => column.validate())).then(() => true);

  const validateByRowIndex = (rowIndex: number | number[]) => {
    const rowIndexList = Array.isArray(rowIndex) ? rowIndex : [rowIndex];

    const columnList = rowIndexList.reduce<IColumnContext[]>((result, index) => {
      result.push(...rowList.value[index]);
      return result;
    }, []);

    return Promise.all(columnList.map((column) => column.validate())).then(() => true);
  };

  const validateByColumnIndex = (columnIndex: number | number[]) => {
    const columnIndexList = Array.isArray(columnIndex) ? columnIndex : [columnIndex];

    const columnList = rowList.value.reduce((result, rowItem) => {
      columnIndexList.forEach((index) => {
        result.push(rowItem[index]);
      });
      return result;
    }, []);

    return Promise.all(columnList.map((column) => column.validate())).then(() => true);
  };

  const validateByField = (field: string | string[]) => {
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

    return Promise.all(columnList.map((column) => column.validate())).then(() => true);
  };

  provide(tableInjectKey, {
    props,
    emits,
    fixedLeft,
    fixedRight,
    columnSizeConfig,
    registerRow,
    updateRow,
    unregisterRow,
    getAllColumnList: () => rowList.value,
    getColumnRelateRowIndexByInstance,
    validate,
    validateByRowIndex,
    validateByColumnIndex,
    validateByField,
  });

  defineExpose<Expose>({
    validate,
    validateByRowIndex,
    validateByColumnIndex,
    validateByField,
  });
</script>
<style lang="less">
  @fixed-column-z-index: 111;
  @scroll-z-index: 200;
  @fixed-wrapper-z-index: 300;

  .bk-editable-table {
    position: relative;
    background: #fff;
    transform: translate(0);

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

      &.fixed-left-column {
        position: sticky;
        left: 0;
      }

      &.fixed-right-column {
        position: sticky;
        right: 0;
      }
    }

    th {
      padding: 0 10px;
      color: #313238;
      background-color: #fafbfd;

      &.fixed-left-column,
      &.fixed-right-column {
        z-index: 9;
        background-color: #fafbfd;
      }

      &:hover {
        background-color: #f0f1f5;
      }
    }

    td {
      padding: 0;

      &.is-fixed {
        z-index: @fixed-column-z-index;
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
    z-index: @fixed-wrapper-z-index;
    overflow-x: hidden;
    pointer-events: none;
    box-shadow: 8px 0 10px -5px rgb(0 0 0 / 12%);
  }

  .bk-editable-table-fixed-right {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: @fixed-wrapper-z-index;
    pointer-events: none;
    box-shadow: -8px 0 10px -5px rgb(0 0 0 / 12%);
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
    z-index: @scroll-z-index;
    height: 14px;
    overflow: scroll hidden;
    cursor: pointer;
    opacity: 0%;
    visibility: hidden;
    transition: 0.15s;

    &.is-show {
      visibility: visible;
    }

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
