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
    field="online_switch_type"
    :label="t('切换模式')"
    :min-width="150"
    required
    :rowspan="rowspan">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="list"
        :title="t('清档类型')"
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
      :list="list" />
  </EditableColumn>
</template>

<script lang="ts">
  export const ONLINE_SWITCH_TYPE = {
    NO_CONFIRM: 'no_confirm',
    USER_CONFIRM: 'user_confirm',
  };
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { Column as EditableColumn, Select as EditableSelect } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    rowspan: number;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const list = [
    {
      label: t('需人工确认'),
      value: ONLINE_SWITCH_TYPE.USER_CONFIRM,
    },
    {
      label: t('无需确认'),
      value: ONLINE_SWITCH_TYPE.NO_CONFIRM,
    },
  ];

  const isShowBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string, 'online_switch_type');
  };
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
