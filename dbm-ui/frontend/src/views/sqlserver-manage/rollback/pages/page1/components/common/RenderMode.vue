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
        v-model="localResotreTime"
        :disabled="editDisabled"
        :disabled-date="disableDate"
        ext-popover-cls="not-seconds-date-picker"
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
          :rules="rules"
          style="flex: 1" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryBackupLogs } from '@services/source/sqlserver';

  import { useTimeZoneFormat } from '@hooks';

  import TableEditDateTime from '@views/mysql/common/edit/DateTime.vue';
  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  interface Props {
    clusterId?: number;
    restoreBackupFile?: ServiceReturnType<typeof queryBackupLogs>[number];
    restoreTime?: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      restore_backup_file?: any;
      restore_time?: string;
    }>;
  }

  const props = defineProps<Props>();

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const { t } = useI18n();
  const formatDateToUTC = useTimeZoneFormat();

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
      id: 'record',
      name: t('备份记录'),
    },
    {
      id: 'time',
      name: t('回档到指定时间'),
    },
  ];

  const localRollbackTimeRef = ref<InstanceType<typeof TableEditDateTime>>();
  const localBackupidRef = ref<InstanceType<typeof TableEditSelect>>();
  const localBackupType = ref('record');
  const localBackupid = ref(0);
  const localResotreTime = ref('');
  const localRestoreBackupFile = ref<Props['restoreBackupFile']>();

  const logRecordList = shallowRef<Array<{ id: string; name: string }>>([]);

  const editDisabled = computed(() => !props.clusterId);

  let logRecordListMemo = [] as any[];

  const fetchLogData = () => {
    logRecordList.value = [];
    logRecordListMemo = [];
    queryBackupLogs({
      cluster_id: 58 || (props.clusterId as number),
      days: 30,
    }).then((dataList) => {
      logRecordList.value = dataList.map((item) => ({
        id: item.backup_id,
        name: item.backup_id,
      }));
      logRecordListMemo = dataList;
    });
  };

  watch(
    () => [props.restoreBackupFile, props.clusterId],
    () => {
      localRestoreBackupFile.value = undefined;
      localResotreTime.value = '';
      if (!props.clusterId) {
        return;
      }
      fetchLogData();
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.restoreBackupFile,
    () => {
      if (props.restoreBackupFile) {
        localRestoreBackupFile.value = props.restoreBackupFile;
      }
      if (props.restoreTime) {
        localResotreTime.value = props.restoreTime;
      }

      localBackupType.value = props.restoreTime ? 'time' : 'record';
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      if (localBackupType.value === 'record') {
        return localBackupidRef.value!.getValue().then(() => {
          const backupInfo = _.find(logRecordListMemo, (item) => item.backup_id === localBackupid.value);
          return {
            restore_backup_file: backupInfo,
          };
        });
      }
      return localRollbackTimeRef.value!.getValue().then(() => ({
        restore_time: formatDateToUTC(localResotreTime.value),
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
