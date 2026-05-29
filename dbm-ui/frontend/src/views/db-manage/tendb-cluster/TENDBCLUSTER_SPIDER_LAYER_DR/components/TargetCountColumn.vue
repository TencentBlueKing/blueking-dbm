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
  <EditableColumn
    :append-rules="rules"
    field="count"
    :label="t('目标数量（台）')"
    :min-width="180"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('目标数量（台）')"
        type="number-input"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :min="min"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    /**
     * 目标数量上限（含）。0 或 undefined 表示不限上限
     */
    max?: number;
    /**
     * 目标数量下限（含），默认 1
     */
    min?: number;
  }

  type Emits = (e: 'batch-edit', value: string[] | string, field: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    max: 0,
    min: 1,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('目标数量不能为空'),
      trigger: 'blur',
      validator: (value: string) => value !== '' && value !== undefined && value !== null,
    },
    {
      message: t('目标数量必须为大于等于n的整数', { n: props.min }),
      trigger: 'blur',
      validator: (value: string) => {
        if (value === '' || value === undefined || value === null) {
          return true;
        }
        const num = Number(value);
        return Number.isInteger(num) && num >= props.min;
      },
    },
    {
      message: t('目标数量不能超过n台', { n: props.max }),
      trigger: 'blur',
      validator: (value: string) => {
        if (!props.max) {
          return true;
        }
        if (value === '' || value === undefined || value === null) {
          return true;
        }
        const num = Number(value);
        return num <= props.max;
      },
    },
  ];

  const showBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string[] | string) => {
    emits('batch-edit', value, 'count');
  };
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
