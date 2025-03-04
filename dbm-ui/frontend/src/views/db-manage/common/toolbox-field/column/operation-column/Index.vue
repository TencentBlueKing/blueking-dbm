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
  <Column
    ref="column"
    fixed="right"
    :label="t('操作')"
    readonly
    :resizeable="false"
    :width="100">
    <div class="toolbox-operation-column">
      <div
        v-if="Boolean(createRowMethod)"
        class="action-btn"
        @click="handleAppend">
        <DbIcon type="plus-fill" />
      </div>
      <div
        class="action-btn"
        :class="{
          disabled: !isRemoveable,
        }"
        @click="handleRemove">
        <DbIcon type="minus-fill" />
      </div>
      <div
        v-bk-tooltips="t('克隆')"
        class="action-btn"
        @click="handleClone">
        <DbIcon type="copy-2" />
      </div>
    </div>
  </Column>
</template>
<script setup lang="ts" generic="T extends Record<string, any>">
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { Column, useTable } from '@components/editable-table/Index.vue';

  const props = defineProps<{
    createRowMethod?: () => T;
  }>();

  const tableData = defineModel<T[]>('tableData', {
    required: true,
  });

  const { t } = useI18n();

  const editTableContext = useTable();
  const columnRef = useTemplateRef('column');

  const isRemoveable = computed(() => tableData.value.length > 1);

  const handleAppend = () => {
    const rowIndex = columnRef.value!.getRowIndex();
    const newRowIndex = rowIndex + 1;

    if (newRowIndex > 0) {
      tableData.value.splice(newRowIndex, 0, props.createRowMethod!());
    }
  };

  const handleRemove = () => {
    if (!isRemoveable.value) {
      return;
    }
    const rowIndex = columnRef.value!.getRowIndex();
    if (rowIndex > -1) {
      tableData.value.splice(rowIndex, 1);
    }
  };

  const handleClone = () => {
    const rowIndex = columnRef.value!.getRowIndex();

    const newRowIndex = rowIndex + 1;

    if (newRowIndex > 0) {
      tableData.value.splice(newRowIndex, 0, _.cloneDeep(tableData.value[rowIndex]));
      editTableContext!.validateByRowIndex(newRowIndex);
    }
  };
</script>
<style lang="less">
  .toolbox-operation-column {
    display: flex;
    height: 42px;
    padding: 0 10px;
    align-items: center;

    .action-btn {
      display: flex;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }

      &.disabled {
        color: #dcdee5;
        cursor: not-allowed;
      }

      & ~ .action-btn {
        margin-left: 12px;
      }
    }
  }
</style>
