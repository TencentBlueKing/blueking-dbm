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
    field="recovery_time_point"
    :label="t('构造到指定时间')"
    required
    :width="240">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('构造到指定时间')">
        <BatchEditDatePick
          v-model="batchEditValue"
          append-to-body
          clearable
          :disabled-date="disableDate"
          type="datetime" />
      </BatchEditColumn>
    </template>
    <EditableDatePicker
      v-model="modelValue"
      append-to-body
      clearable
      :disabled-date="disableDate"
      type="datetime" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn, { BatchEditDatePick } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const batchEditValue = ref('');

  const disableDate = (date: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'recovery_time_point');
  };
</script>
<style lang="less" scoped>
  .render-box {
    :deep(.icon-wrapper) {
      left: 10px;
      display: block;
      width: 32px;
    }

    :deep(input) {
      padding-left: 40px;
    }
  }
</style>
