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
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    field="count"
    :label="t('构造主机数量')"
    required
    :width="200">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('构造主机数量')">
        <BatchEditNumberInput v-model="batchEditValue" />
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :max="max"
      type="number" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditNumberInput } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    max: number;
  }

  type Emits = (e: 'batch-edit', value: number, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('构造主机数量不能为空'),
      trigger: 'change',
      validator: (value: number) => Boolean(value),
    },
    {
      message: t('不能超过实例数'),
      trigger: 'change',
      validator: (value: number) => Number(value) <= props.max,
    },
  ];

  const batchEditValue = ref(0);

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'count');
  };
</script>
