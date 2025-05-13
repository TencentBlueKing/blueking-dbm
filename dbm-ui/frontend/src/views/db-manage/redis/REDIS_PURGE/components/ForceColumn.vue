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
    field="force"
    :label="t('强制清档')"
    required
    :width="200">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="selectList"
        :title="t('强制清档')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :list="selectList" />
  </EditableColumn>
</template>

<script lang="ts">
  export const ForceType = {
    NO: '0',
    YES: '1',
  };
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const selectList = [
    {
      label: t('是'),
      value: ForceType.YES,
    },
    {
      label: t('否'),
      value: ForceType.NO,
    },
  ];

  const isShowBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string, 'force');
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
