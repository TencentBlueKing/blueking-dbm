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
    id="toolboxRenderTableKey"
    ref="tableOuterRef"
    class="toolbox-render-table">
    <table ref="tableRef">
      <thead>
        <tr style="position: relative">
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
<script lang="ts">
  import type { InjectionKey, Ref } from 'vue';

  export const renderTablekey: InjectionKey<{ isOverflow: Ref<boolean>; rowWidth: Ref<number> }> =
    Symbol('renderTable');
</script>

<script setup lang="ts">
  import _ from 'lodash';

  import useColumnResize from './hooks/useColumnResize';

  const checkTableScroll = () => {
    // handleScroll();
    rowWidth.value = tableRef.value.clientWidth;
    isOverflow.value = tableOuterRef.value.clientWidth < tableRef.value.clientWidth;
    initColumnWidth();
  };

  const tableOuterRef = ref();
  const tableRef = ref();
  const tableColumnResizeRef = ref();
  const isOverflow = ref(false);
  const rowWidth = ref(0);
  // const isScrollToLeft = ref(true);
  // const isScrollToRight = ref(false);

  const { initColumnWidth } = useColumnResize(tableOuterRef, tableColumnResizeRef, _.debounce(checkTableScroll));

  provide(renderTablekey, {
    isOverflow,
    rowWidth,
  });

  // const handleScroll = () => {
  //   isScrollToLeft.value = tableOuterRef.value.scrollLeft === 0;
  // eslint-disable-next-line max-len,
  //   isScrollToRight.value = (tableOuterRef.value.scrollWidth - tableOuterRef.value.scrollLeft) < tableOuterRef.value.clientWidth + 1;
  // };

  onMounted(() => {
    window.addEventListener('resize', checkTableScroll);
    checkTableScroll();
    setTimeout(() => checkTableScroll());
  });

  onBeforeUnmount(() => window.removeEventListener('resize', checkTableScroll));
</script>
<style lang="less">
  .toolbox-render-table {
    position: relative;
    width: 100%;
    overflow-x: auto;

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
        border-top: 1px solid #dcdee5;
        border-left: 1px solid #dcdee5;
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
        content: '*';
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
