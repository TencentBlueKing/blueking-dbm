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
    field="startTime"
    :label="t('回档时间')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :title="t('回档时间')"
        type="datetime"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <DatePicker
      v-model="modelValue"
      :disable-date="disableDate"
      type="datetime" />
  </Column>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import { Column, DatePicker } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: string, field: string): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    emits('batch-edit', value, 'startTime');
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
