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
    field="backup_source"
    :label="t('备份源')"
    :min-width="100"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="backupSourceList"
        :title="t('备份源')"
        type="select"
        @change="handleBatchEdit" />
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select"
        @click="handleShowBatchEdit">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableSelect
      v-model="modelValue"
      :list="backupSourceList"
      @change="handleChange" />
  </EditableColumn>
</template>
<script lang="ts">
  export enum BACKUP_SOURCE {
    LOCAL = 'local',
    REMOTE = 'remote',
  }
</script>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  type Emits = (e: 'batch-edit', data: typeof modelValue.value, field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: BACKUP_SOURCE.REMOTE,
  });

  const { t } = useI18n();

  const backupSourceList = [
    {
      label: t('远程备份'),
      value: BACKUP_SOURCE.REMOTE,
    },
    {
      label: t('本地备份'),
      value: BACKUP_SOURCE.LOCAL,
    },
  ];

  const isShowBatchEdit = ref(false);

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string) => {
    emits('batch-edit', value, 'backup_source');
  };

  const handleChange = (value: string) => {
    modelValue.value = value;
  };
</script>
<style lang="less" scoped>
  .batch-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
