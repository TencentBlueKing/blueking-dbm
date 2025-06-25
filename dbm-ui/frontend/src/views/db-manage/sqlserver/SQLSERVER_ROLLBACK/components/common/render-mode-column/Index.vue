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
        :title="t('回档类型')"
        type="datetime"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
        <template #content>
          <div
            class="title-spot edit-title"
            style="font-weight: normal">
            {{ t('回档类型') }} <span class="required" />
          </div>
          <BkSelect
            v-model="batchBackupType"
            :clearable="false"
            filterable
            :list="targetList"
            @change="handleBatchBackupTypeChange" />
          <div v-if="batchBackupType === 'record'">
            <div
              class="title-spot edit-title mt-24"
              style="font-weight: normal">
              {{ t('备份文件 (批量编辑仅支持 “指定时间自动匹配” )') }} <span class="required" />
            </div>
            <BkDatePicker
              v-model="batchTimePickValue"
              :clearable="false"
              :placeholder="t('如：2019-01-30 12:12:21')"
              style="width: 361px"
              type="datetime" />
            <div
              class="mt-4"
              :style="{ color: '#979ba5', lineHeight: '20px' }">
              {{ t('自动匹配指定日期前的最新全库备份') }}
            </div>
          </div>
          <div v-else>
            <div
              class="title-spot edit-title mt-24"
              style="font-weight: normal">
              {{ t('时间') }} <span class="required" />
            </div>
            <BkDatePicker
              v-model="batchTimePickValue"
              :clearable="false"
              :disabled-date="disableDate"
              :placeholder="t('如：2019-01-30 12:12:21')"
              style="width: 361px"
              type="datetime" />
          </div>
        </template>
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
          v-model:auto-match-date-time="autoMatchDateTime"
          v-model:record-type="recordType"
          :cluster-id="clusterId"
          :disabled="editDisabled"
          @datetime-confirm="handleDatetimeConfirm" />
      </div>
    </div>
  </EditableColumn>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs } from '@services/source/sqlserver';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import RecordSelector, { OperateType } from './RecordSelector.vue';

  interface Props {
    clusterId?: number;
  }

  type Emits = (
    e: 'batch-edit',
    value: {
      time: string;
      type: string;
    },
    field: string,
  ) => void;

  interface Expose {
    setRecordByBatch: (time: string) => void;
  }

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
      message: '',
      trigger: 'change',
      validator: () => {
        if (localBackupType.value === 'time') {
          return true;
        }
        if (!props.clusterId) {
          return t('请先设置集群');
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
  const batchTimePickValue = ref('');
  const batchBackupType = ref('record');
  const autoMatchDateTime = ref('');
  const recordType = ref(OperateType.MANUAL);

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

  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

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

  const handleBatchEditChange = () => {
    isInit = false;
    emits(
      'batch-edit',
      {
        time: batchTimePickValue.value,
        type: batchBackupType.value,
      },
      'restore_time',
    );
  };

  const handleBatchBackupTypeChange = () => {
    batchTimePickValue.value = '';
  };

  defineExpose<Expose>({
    setRecordByBatch(time: string) {
      nextTick(() => {
        autoMatchDateTime.value = time;
        recordType.value = OperateType.MATCH;
        if (props.clusterId) {
          handleDatetimeConfirm();
        }
      });
    },
  });
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
