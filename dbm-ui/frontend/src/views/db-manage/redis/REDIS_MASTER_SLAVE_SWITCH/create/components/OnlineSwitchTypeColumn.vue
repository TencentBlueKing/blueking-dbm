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
    required
    :width="200">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="list"
        :title="t('切换模式')"
        type="select"
        @change="handleBatchEditChange">
        <BkButton
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          text
          theme="primary"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </BkButton>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :list="list" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Emits {
    (e: 'batch-edit', value: string): void;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  enum OnlineSwitchType {
    USER_CONFIRM = 'user_confirm',
    NO_CONFIRM = 'no_confirm',
  }

  const list = [
    {
      value: OnlineSwitchType.USER_CONFIRM,
      label: t('需人工确认'),
    },
    {
      value: OnlineSwitchType.NO_CONFIRM,
      label: t('无需确认'),
    },
  ];

  const isShowBatchEdit = ref(false);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string);
  };
</script>
