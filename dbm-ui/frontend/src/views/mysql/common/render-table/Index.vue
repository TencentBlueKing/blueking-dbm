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
    ref="tableRef"
    class="mysql-tool-render-table">
    <table>
      <thead>
        <tr>
          <slot />
        </tr>
      </thead>
      <slot name="data" />
    </table>
    <div
      ref="tableColumnResizeRef"
      class="table-column-resize" />
  </div>
</template>
<script setup lang="ts">
  import {
    onMounted,
    provide,
    ref,
  } from 'vue';

  import useColumnResize from './hooks/useColumnResize';

  const tableRef = ref();
  const tableColumnResizeRef = ref();

  const  {
    initColumnWidth,
    handleMouseDown,
    handleMouseMove,
  } = useColumnResize(tableRef, tableColumnResizeRef);

  onMounted(() => {
    initColumnWidth();
  });

  provide('mysqlToolRenderTable', {
    columnMousedown: handleMouseDown,
    columnMouseMove: handleMouseMove,
  });
</script>
<style lang="less">
  .mysql-tool-render-table {
    position: relative;
    overflow-x: auto;

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
