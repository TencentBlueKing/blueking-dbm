<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    class="bk-editable-table"
    @click="handleUserChange">
    <div
      ref="table"
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
      <div
        v-if="slots.empty"
        class="bk-editable-table-empty">
        <slot name="empty" />
      </div>
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
      ref="resizePlaceholder"
      class="bk-editable-column-resize" />

    <div class="bk-edit-table-scroll">
      <div
        ref="scrollX"
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

  import { useEventBus } from '@hooks';

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
  import useRowspan, { type IRowspanTask } from './hooks/use-rowspan';
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
    empty?(): VNode;
  }

  export interface Expose {
    clearValidate: () => void;
    validate: () => Promise<boolean>;
    validateByColumnIndex: (row: number | number[]) => Promise<boolean>;
    validateByField: (row: string | string[]) => Promise<boolean>;
    validateByRowIndex: (row: number | number[]) => Promise<boolean>;
    viewError: (errorList: { errors: string; field: string; row_key: string | number }[]) => void;
  }

  export const tableInjectKey: InjectionKey<
    {
      columnSizeConfig: Ref<Record<string, { renderWidth: number }>>;
      emits: Emits;
      fixedLeft: Ref<boolean>;
      fixedRight: Ref<boolean>;
      getAllColumnList: () => IColumnContext[][];
      getColumnRelateRowIndexByInstance: (columnInstance: ComponentInternalInstance) => number;
      props: Props;
      pushRowspanTask: (task: IRowspanTask) => void;
      registerRow: (rowColumnList: IColumnContext[], rowElement: HTMLElement) => void;
      removeRowspanTask: (run: IRowspanTask['run']) => void;
      runRowspanTask: () => void;
      unregisterRow: (rowColumnList: IColumnContext[]) => void;
      updateRow: () => void;
    } & Expose
  > = Symbol.for('bk-editable-table');

  export { Block, Column, DatePicker, Input, Row, Select, TagInput, Textarea, TimePicker, useColumn, useTable };

  export const getColumnCount = (() => {
    let count = 0;
    return () => count++;
  })();
</script>
<script setup lang="ts">
  defineOptions({
    name: 'EditableTable',
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const slots = defineSlots<Slots>();

  const eventBus = useEventBus();

  const tableRef = useTemplateRef<HTMLElement>('table');
  const scrollXRef = useTemplateRef<HTMLElement>('scrollX');
  const resizePlaceholderRef = useTemplateRef<HTMLElement>('resizePlaceholder');
  const tableWidth = ref<'auto' | number>('auto');

  const columnList = shallowRef<IColumnContext[]>([]);
  const rowList = shallowRef<IColumnContext[][]>([]);

  const isShowScrollX = ref(true);
  const isUserChange = ref(false);

  const { columnSizeConfig, handleMouseDown, handleMouseMove } = useResize(tableRef, resizePlaceholderRef, columnList);
  const { fixedLeft, fixedRight, initalScroll, leftFixedStyles, rightFixedStyles } = useScroll(tableRef);
  const { pushRowspanTask, removeRowspanTask, runRowspanTask } = useRowspan();

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
          if (scrollXRef.value) {
            isShowScrollX.value = scrollXRef.value.offsetWidth + 2 < scrollXRef.value.scrollWidth;
          }
        });
        initalScroll();
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => props.model,
    () => {
      if (isUserChange.value) {
        window.changeConfirm = true;
      }
      eventBus.emit('editable-table-model-change');
    },
    {
      deep: true,
    },
  );

  const handleUserChange = () => {
    isUserChange.value = true;
  };

  // 行的注册顺序不一定与 DOM 顺序一致，按 DOM 位置插入保证行序正确
  const registerRow = (rowColumnList: IColumnContext[], rowElement: HTMLElement) => {
    const index = _.indexOf(rowElement.parentElement?.children, rowElement);
    const latestRowList = [...rowList.value];
    if (index > -1) {
      latestRowList.splice(index, 0, rowColumnList);
    } else {
      latestRowList.push(rowColumnList);
    }
    rowList.value = latestRowList;
  };

  const updateRow = _.throttle(() => {
    columnList.value = rowList.value.length > 0 ? [...rowList.value[0]!] : [];
  }, 20);

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

  // 与 DbForm 的验证协议保持一致：任一单元格验证不通过时 reject，全部通过 resolve(true)
  const validateColumnList = (validateColumn: IColumnContext[]) =>
    Promise.all(validateColumn.map((column) => column.validate())).then(() => true);

  const validate = () => validateColumnList(_.flatten(rowList.value));

  const validateByRowIndex = (rowIndex: number | number[]) => {
    const rowIndexList = Array.isArray(rowIndex) ? rowIndex : [rowIndex];

    const columnList = rowIndexList.reduce<IColumnContext[]>((result, index) => {
      result.push(...(rowList.value[index] || []));
      return result;
    }, []);

    return validateColumnList(columnList);
  };

  const validateByColumnIndex = (columnIndex: number | number[]) => {
    const columnIndexList = Array.isArray(columnIndex) ? columnIndex : [columnIndex];

    const columnList = rowList.value.reduce<IColumnContext[]>((result, rowItem) => {
      columnIndexList.forEach((index) => {
        const column = rowItem[index];
        if (column) {
          result.push(column);
        }
      });
      return result;
    }, []);

    return validateColumnList(columnList);
  };

  const validateByField = (field: string | string[]) => {
    const fieldList = Array.isArray(field) ? field : [field];

    const columnList = rowList.value.reduce<IColumnContext[]>((result, rowItem) => {
      fieldList.forEach((field) => {
        rowItem.forEach((column) => {
          if (column.props.field && column.props.field === field) {
            result.push(column);
          }
        });
      });
      return result;
    }, []);

    return validateColumnList(columnList);
  };

  const clearValidate = () => {
    _.flatten(rowList.value).forEach((column) => column.clearValidate());
  };

  const viewError = (errorList: Parameters<Expose['viewError']>[0]) => {
    // 展示新的错误前清理上一次遗留的错误态
    clearValidate();
    // 后端校验无法保证 row index 的正确性，需要通过 row key 来标记每一行数据
    // 优先通过 props.model 将 row key 转换成 row index
    const errorRowKeyMap = errorList.reduce<Record<string, (typeof errorList)[number]>>((result, item) => {
      return Object.assign(result, {
        [item.row_key]: item,
      });
    }, {});
    const errorRowIndexMap = props.model.reduce<Record<string, (typeof errorList)[number]>>((result, item, index) => {
      if (item?.row_key && errorRowKeyMap[item.row_key]) {
        Object.assign(result, {
          [index]: errorRowKeyMap[item.row_key],
        });
      }
      return result;
    }, {});
    const allRowList = Array.from(tableRef.value!.querySelectorAll('tbody.bk-editable-table-body > tr') || []);

    Object.keys(errorRowIndexMap).forEach((rowIndex) => {
      const rowEle = allRowList[Number(rowIndex)];
      if (!rowEle) {
        return;
      }
      Array.from(rowEle.querySelectorAll('td.bk-editable-table-body-column') || []).forEach((tdEle) => {
        // eslint-disable-next-line no-underscore-dangle
        const getColumnInstance = (tdEle as any).__getCurrentInstance__;
        if (!_.isFunction(getColumnInstance)) {
          return;
        }
        const columnInstance = getColumnInstance();
        if (!columnInstance) {
          return;
        }
        const errorInfo = errorRowIndexMap[rowIndex];
        columnInstance.exposeProxy.viewError(errorInfo.errors, errorInfo.field);
      });
    });
  };

  provide(tableInjectKey, {
    clearValidate,
    columnSizeConfig,
    emits,
    fixedLeft,
    fixedRight,
    getAllColumnList: () => rowList.value,
    getColumnRelateRowIndexByInstance,
    props,
    pushRowspanTask,
    registerRow,
    removeRowspanTask,
    runRowspanTask,
    unregisterRow,
    updateRow,
    validate,
    validateByColumnIndex,
    validateByField,
    validateByRowIndex,
    viewError,
  });

  onBeforeUnmount(() => {
    window.changeConfirm = false;
  });

  defineExpose<Expose>({
    clearValidate,
    validate,
    validateByColumnIndex,
    validateByField,
    validateByRowIndex,
    viewError,
  });
</script>
<style lang="less">
  .bk-editable-table {
    --table-scroll-z-index: 200;
    --table-fixed-wrapper-z-index: 300;
    --table-border-color: #dcdee5;
    --column-head-backgroud-color: #f0f1f5;
    --column-head-hover-backgroud-color: #eaebf0;
    --column-background-color: #fff;

    position: relative;
    transform: translate(0);

    &::before {
      position: absolute;
      z-index: 9;
      pointer-events: none;
      border-right: 1px solid var(--table-border-color);
      border-left: 1px solid var(--table-border-color);
      content: '';
      inset: 0;
    }

    .bk-editable-table-wrapper {
      overflow: scroll hidden;

      &::-webkit-scrollbar {
        width: 0;
        height: 0;
      }

      .bk-editable-table-empty {
        display: flex;
        justify-content: center;
        align-items: center;
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
        border: 1px solid var(--table-border-color);
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
      background-color: var(--column-head-backgroud-color);

      &.fixed-left-column,
      &.fixed-right-column {
        z-index: 9;
        background-color: var(--column-head-backgroud-color);
      }

      &:hover {
        background-color: var(--column-head-hover-backgroud-color);
      }
    }

    td {
      padding: 0;
      background: var(--column-background-color);
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
    z-index: var(--table-fixed-wrapper-z-index);
    overflow-x: hidden;
    pointer-events: none;
    box-shadow: 8px 0 10px -5px rgb(0 0 0 / 12%);
  }

  .bk-editable-table-fixed-right {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: var(--table-fixed-wrapper-z-index);
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
    z-index: var(--table-scroll-z-index);
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
      height: 3px;
      transition: 0.15s;
    }

    &::-webkit-scrollbar-thumb {
      background-color: rgb(151 155 165 / 80%);
      border-radius: 2px;
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
