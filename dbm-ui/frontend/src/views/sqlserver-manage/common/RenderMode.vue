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
  <div class="render-mode">
    <div class="action-item">
      <TableEditSelect
        v-model="localBackupType"
        :disabled="editDisabled"
        :list="targetList" />
    </div>
    <div class="action-item">
      <TableEditDateTime
        v-if="localBackupType === 'time'"
        ref="localRollbackTimeRef"
        v-model="resotreTime"
        :disabled="editDisabled"
        :disabled-date="disableDate"
        :rules="timerRules"
        type="datetime" />
      <div
        v-else
        class="local-backup-select">
        <DbIcon
          class="file-flag"
          type="wenjian" />
        <TableEditSelect
          ref="localBackupidRef"
          v-model="localBackupid"
          :disabled="editDisabled"
          :list="logRecordList"
          :popover-min-width="300"
          :rules="rules"
          style="flex: 1"
          @change="(value: any) => handleBackupidChange(value as string)" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs } from '@services/source/sqlserver';

  import { useTimeZoneFormat } from '@hooks';

  import { useTimeZone } from '@stores';

  import TableEditDateTime from '@components/render-table/columns/DateTime.vue';
  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  interface Props {
    clusterId?: number;
  }

  interface Exposes {
    getValue: () => Promise<{
      restore_backup_file?: any;
      restore_time?: string;
    }>;
  }

  const props = defineProps<Props>();

  const disableDate = (date: Date) =>
    date && (dayjs(date).isAfter(dayjs()) || dayjs(date).isBefore(dayjs().subtract(15, 'day')));

  const { t } = useI18n();
  const formatDateToUTC = useTimeZoneFormat();
  const timeZoneStore = useTimeZone();

  const timerRules = [
    {
      validator: (value: string) => !!value,
      message: t('回档时间不能为空'),
    },
  ];

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('备份记录不能为空'),
    },
  ];

  const targetList = [
    {
      value: 'record',
      label: t('备份记录'),
    },
    {
      value: 'time',
      label: t('回档到指定时间'),
    },
  ];

  const restoreBackupFile = defineModel<ServiceReturnType<typeof queryBackupLogs>[number]>('restoreBackupFile');
  const resotreTime = defineModel<string>('restoreTime', {
    default: '',
  });

  const localRollbackTimeRef = ref<InstanceType<typeof TableEditDateTime>>();
  const localBackupidRef = ref<InstanceType<typeof TableEditSelect>>();
  const localBackupType = ref('record');
  const localBackupid = ref(0);

  const logRecordList = shallowRef<Array<{ value: string; label: string }>>([]);

  const editDisabled = computed(() => !props.clusterId);

  let logRecordListMemo = [] as ServiceReturnType<typeof queryBackupLogs>;

  const fetchLogData = () => {
    if (!props.clusterId) {
      return;
    }
    logRecordList.value = [];
    logRecordListMemo = [];
    queryBackupLogs({
      cluster_id: props.clusterId,
      days: 30,
    }).then((dataList) => {
      logRecordList.value = dataList.map((item) => ({
        value: item.backup_id,
        label: `${item.role} ${dayjs(item.start_time).tz(timeZoneStore.label).format('YYYY-MM-DD HH:mm:ss ZZ')}`,
      }));
      logRecordListMemo = dataList;
    });
  };

  watch(
    () => props.clusterId,
    () => {
      restoreBackupFile.value = undefined;
      resotreTime.value = '';
      fetchLogData();
    },
    {
      immediate: true,
    },
  );

  watch(
    [resotreTime, restoreBackupFile],
    () => {
      localBackupType.value = resotreTime.value ? 'time' : 'record';
    },
    {
      immediate: true,
    },
  );

  const handleBackupidChange = (id: string) => {
    restoreBackupFile.value = _.find(logRecordListMemo, (item) => item.backup_id === id);
  };

  defineExpose<Exposes>({
    getValue() {
      if (localBackupType.value === 'record') {
        return localBackupidRef.value!.getValue().then(() => ({
          restore_backup_file: restoreBackupFile.value,
        }));
      }
      return localRollbackTimeRef.value!.getValue().then(() => ({
        restore_time: formatDateToUTC(resotreTime.value),
      }));
    },
  });
</script>
<style lang="less" scoped>
  .render-mode {
    display: flex;

    .action-item {
      flex: 0 0 50%;
      overflow: hidden;
    }
  }

  .local-backup-select {
    position: relative;

    :deep(.table-edit-select) {
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
