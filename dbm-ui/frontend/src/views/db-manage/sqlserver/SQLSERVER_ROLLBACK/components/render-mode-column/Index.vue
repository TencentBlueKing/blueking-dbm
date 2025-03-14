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
    ref="editableColumn"
    :append-rules="rules"
    field="restore_time"
    :label="t('回档类型')"
    :min-width="400"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :disable-fn="disableDate"
        :title="t('回档到指定时间')"
        type="datetime"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <div style="width: 140px">
      <EditableSelect
        v-model="localBackupType"
        :disabled="editDisabled"
        :list="targetList"
        @change="hanldeBackupTypeChange" />
    </div>
    <div style="flex: 1">
      <EditableDatePicker
        v-if="localBackupType === 'time'"
        v-model="restoreTime"
        :disabled="editDisabled"
        :disabled-date="disableDate"
        type="datetime"
        @change="handleRestoreTimeChange" />

      <div
        v-else
        class="local-backup-select">
        <RecordSelector
          ref="localBackupFileRef"
          v-model="restoreBackupFile"
          :cluster-id="clusterId"
          :disabled="editDisabled"
          @datetime-confirm="handleDatetimeConfirm" />
      </div>
    </div>
  </EditableColumn>
</template>
<script setup lang="tsx">
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs } from '@services/source/sqlserver';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import RecordSelector from './RecordSelector.vue';

  interface Props {
    clusterId?: number;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const restoreBackupFile = defineModel<ServiceReturnType<typeof queryBackupLogs>[number]>('restoreBackupFile');
  const restoreTime = defineModel<string>('restoreTime', {
    default: '',
  });

  const { t } = useI18n();

  const editableColumnRef = useTemplateRef('editableColumn');
  const localBackupFileRef = useTemplateRef('localBackupFileRef');

  let isInit = true;

  const rules = [
    {
      message: '',
      required: true,
      trigger: 'change',
      validator: () => {
        if (localBackupType.value === 'time') {
          return restoreTime.value ? true : t('回档时间不能为空');
        }
        return localBackupFileRef.value!.validateManual() ? true : t('备份记录不能为空');
      },
    },
    {
      message: t('暂无与指定时间最近的备份记录'),
      trigger: 'change',
      validator: () => {
        if (localBackupType.value === 'time') {
          return true;
        }
        return localBackupFileRef.value!.validateMatchLog();
      },
    },
  ];

  const targetList = [
    {
      label: t('备份记录'),
      value: 'record',
    },
    {
      label: t('回档到指定时间'),
      value: 'time',
    },
  ];

  const isShowBatchEdit = ref(false);
  const localBackupType = ref('record');

  const editDisabled = computed(() => !props.clusterId);

  watch(
    () => props.clusterId,
    () => {
      if (!isInit) {
        restoreBackupFile.value = undefined;
        restoreTime.value = '';
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    [restoreTime, restoreBackupFile],
    () => {
      localBackupType.value = restoreTime.value ? 'time' : 'record';
    },
    {
      immediate: true,
    },
  );

  const disableDate = (date?: Date | number) => Boolean(date && date.valueOf() > Date.now());

  const hanldeBackupTypeChange = () => {
    restoreTime.value = '';
  };

  const handleRestoreTimeChange = () => {
    isInit = false;
  };

  const handleDatetimeConfirm = () => {
    editableColumnRef.value!.validate();
    isInit = false;
  };

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    isInit = false;
    emits('batch-edit', value as string, 'restore_time');
  };
</script>
<style lang="less" scoped>
  .render-mode {
    display: flex;

    .action-item {
      overflow: hidden;

      &:first-child {
        flex: 1;
      }

      &:last-child {
        flex: 2;
      }
    }
  }

  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .local-backup-select {
    position: relative;

    :deep(.table-edit-select),
    :deep(.rollback-mode-select) {
      .select-result-text {
        padding-left: 14px;
      }

      .select-placeholder {
        left: 30px;
      }
    }

    .file-flag {
      position: absolute;
      top: 14px;
      left: 8px;
      z-index: 1;
      font-size: 16px;
      color: #c4c6cc;
    }
  }
</style>
