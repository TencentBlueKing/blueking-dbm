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
            columnSizeConfig[columnItem.key]!.renderWidth > 0
              ? `${columnSizeConfig[columnItem.key]!.renderWidth}px`
              : '',
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
