<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    id="mysqlToolRenderTable"
    ref="tableOuterRef"
    class="mysql-tool-render-table">
    <table
      ref="tableRef">
      <thead>
        <tr style="position:relative;">
          <slot
            :is-overflow="isOverflow"
            :row-width="rowWidth" />
        </tr>
      </thead>
      <slot
        :is-overflow="isOverflow"
        name="data"
        :row-width="rowWidth" />
    </table>
    <div
      ref="tableColumnResizeRef"
      class="table-column-resize" />
  </div>
</template>
<script setup lang="ts">
  import useColumnResize from './hooks/useColumnResize';

  const tableOuterRef = ref();
  const tableRef = ref();
  const tableColumnResizeRef = ref();
  const isOverflow = ref(false);
  const rowWidth = ref(0);

  const  {
    initColumnWidth,
    handleMouseDown,
    handleMouseMove,
  } = useColumnResize(tableOuterRef, tableColumnResizeRef);

  const checkTableScroll = () =>  {
    rowWidth.value = tableRef.value.clientWidth;
    isOverflow.value = tableOuterRef.value.clientWidth < tableRef.value.clientWidth;
  };

  onMounted(() => {
    window.addEventListener('resize', checkTableScroll);
    initColumnWidth();
    checkTableScroll();
    setTimeout(() => checkTableScroll());
  });

  onBeforeUnmount(() => window.removeEventListener('resize', checkTableScroll));

  provide('mysqlToolRenderTable', {
    columnMousedown: handleMouseDown,
    columnMouseMove: handleMouseMove,
  });
</script>
<style lang="less">
  .mysql-tool-render-table {
    position: relative;
    width: 100%;
    overflow-x: auto;
    table-layout: fixed;

    &::-webkit-scrollbar {
      width: 4px;
      height: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: #ddd;
      border-radius: 20px;
      box-shadow: inset 0 0 6px rgb(204 204 204 / 30%);
    }

    table {
      width: 100%;
      font-size: 12px;
      text-align: left;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      table-layout: fixed;

      th,
      td {
        padding: 0 16px;
        line-height: 40px;

        &:nth-child(n+2) {
          border-left: 1px solid #dcdee5;
        }
      }

      th {
        height: 40px;
        font-weight: normal;
        line-height: 0;
        color: #313238;
        background: #f0f1f5;

        .th-cell {
          display: inline-block;
          max-width: 100%;
          overflow: hidden;
          line-height: 40px;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      td {
        border-top: 1px solid #dcdee5;
      }
    }

    .edit-required {
      position: relative;

      &::after {
        position: absolute;
        top: 0;
        margin-left: 4px;
        font-size: 12px;
        line-height: 40px;
        color: #ea3636;
        content: "*";
      }
    }

    .table-column-resize {
      position: absolute;
      top: 0;
      bottom: 0;
      display: none;
      width: 1px;
      background: #dfe0e5;
    }
  }
</style>
