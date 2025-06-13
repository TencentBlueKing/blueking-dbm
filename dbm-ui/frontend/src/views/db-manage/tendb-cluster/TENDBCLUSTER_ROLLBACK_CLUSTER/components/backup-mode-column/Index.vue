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
    :label="t('回档类型')"
    :min-width="400"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('回档类型')"
        @change="handleBatchEdit">
        <template #content>
          <div
            class="title-spot edit-title"
            style="font-weight: normal">
            {{ t('回档类型') }} <span class="required" />
          </div>
          <BkSelect
            v-model="checkedModeType"
            :clearable="false"
            filterable
            :list="backupTypeList"
            @change="handleModeType" />
          <div v-if="checkedModeType === ROLLBACK_TYPE.REMOTE_AND_TIME">
            <div
              class="title-spot edit-title mt-24"
              style="font-weight: normal">
              {{ t('时间') }} <span class="required" />
            </div>
            <BkDatePicker
              :clearable="false"
              :disabled-date="disableDate"
              :placeholder="t('如：2019-01-30 12:12:21')"
              style="width: 361px"
              type="datetime"
              :value="datePickerValue"
              @change="handleDatePickerChange" />
          </div>
          <div v-else>
            <div
              class="title-spot edit-title mt-24"
              style="font-weight: normal">
              {{ t('备份文件 (批量编辑仅支持 “指定时间自动匹配” )') }} <span class="required" />
            </div>
            <BkDatePicker
              :clearable="false"
              :disabled-date="disableDate"
              :placeholder="t('如：2019-01-30 12:12:21')"
              style="width: 361px"
              type="datetime"
              :value="datePickerValue"
              @change="handleDatePickerChange" />
            <div
              class="mt-4"
              :style="{ color: '#979ba5', lineHeight: '20px' }">
              {{ t('自动匹配指定日期前的最新全库备份') }}
            </div>
          </div>
        </template>
      </BatchEditColumn>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select"
        @click="handleShowBatchEdit">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <div class="flex-row">
      <EditableSelect
        v-model="modelValue.rollback_type"
        :list="backupTypeList"
        style="flex: 1"
        @change="handleChangeType" />
      <div style="flex: 2">
        <EditableDatePicker
          v-if="modelValue.rollback_type === ROLLBACK_TYPE.REMOTE_AND_TIME"
          v-model="modelValue.rollback_time"
          :disabled-date="disableDate"
          :placeholder="t('请选择回档时间')"
          type="datetime"
          @change="handleChangeRollbackTime" />
        <div v-else>
          <RecordSelector
            :key="cluster.id"
            ref="recordSelector"
            v-model:backupinfo="modelValue.backupinfo"
            backup-source="remote"
            :backupid="modelValue.backupid"
            :cluster-id="cluster.id" />
        </div>
      </div>
    </div>
  </EditableColumn>
</template>
<script lang="ts">
  export enum ROLLBACK_TYPE {
    REMOTE_AND_BACKUPID = 'REMOTE_AND_BACKUPID',
    REMOTE_AND_TIME = 'REMOTE_AND_TIME',
  }
</script>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import { useTimeZoneFormat } from '@hooks';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import RecordSelector from './RecordSelector.vue';

  interface Props {
    cluster: {
      id: number;
    };
  }

  type Emits = (e: 'batch-edit', data: typeof modelValue.value, field: string) => void;

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    backupid?: string;
    backupinfo?: BackupLogRecord;
    rollback_time?: string;
    rollback_type: string;
  }>({
    default: () => ({
      rollback_type: ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
    }),
  });

  const { format: formatDateToUTC } = useTimeZoneFormat();
  const { t } = useI18n();
  const recordSelector = useTemplateRef('recordSelector');

  const backupTypeList = [
    {
      label: t('备份记录'),
      value: ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
    },
    {
      label: t('回档到指定时间'),
      value: ROLLBACK_TYPE.REMOTE_AND_TIME,
    },
  ];

  const isShowBatchEdit = ref(false);
  const checkedModeType = ref(ROLLBACK_TYPE.REMOTE_AND_BACKUPID);
  const datePickerValue = ref('');

  watch(
    () => modelValue.value.backupid,
    (backupid) => {
      if (backupid) {
        recordSelector.value?.getData(backupid).then((data) => {
          modelValue.value.backupinfo = data;
        });
      }
    },
  );

  const disableDate = (date: number | Date) => {
    const parsedDate = typeof date === 'number' ? new Date(date) : date;
    return dayjs(parsedDate).isAfter(dayjs(), 'day');
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleModeType = (value: ROLLBACK_TYPE) => {
    checkedModeType.value = value;
  };

  const handleDatePickerChange = (date: string) => {
    datePickerValue.value = date;
  };

  const handleBatchEdit = () => {
    if (checkedModeType.value === ROLLBACK_TYPE.REMOTE_AND_TIME) {
      emits(
        'batch-edit',
        {
          rollback_time: formatDateToUTC(datePickerValue.value),
          rollback_type: ROLLBACK_TYPE.REMOTE_AND_TIME,
        },
        'rollback',
      );
    } else {
      emits(
        'batch-edit',
        {
          backupid: datePickerValue.value,
          rollback_type: ROLLBACK_TYPE.REMOTE_AND_BACKUPID,
        },
        'rollback',
      );
    }
  };

  const handleChangeType = (value: string) => {
    modelValue.value = {
      backupid: undefined,
      backupinfo: undefined,
      rollback_time: undefined,
      rollback_type: value,
    };
  };

  const handleChangeRollbackTime = (date: string) => {
    modelValue.value.rollback_time = formatDateToUTC(date);
  };
</script>
<style lang="less" scoped>
  .batch-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .flex-row {
    display: flex;
    width: 100%;
    align-items: center;
  }
</style>
