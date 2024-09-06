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
        :list="backupTypeList"
        :rules="rules"
        @change="hanldeBackupTypeChange" />
    </div>
    <div class="action-item">
      <TableEditDateTime
        v-if="localBackupType === BackupTypes.TIME"
        ref="localRollbackTimeRef"
        v-model="localRollbackTime"
        :disabled="editDisabled"
        :disabled-date="disableDate"
        :rules="rules"
        type="datetime" />

      <div
        v-else
        class="local-backup-select">
        <DbIcon
          class="file-flag"
          type="wenjian" />
        <RecordSelector
          ref="localBackupFileRef"
          :backup-source="backupSource"
          :backupid="backupid"
          :cluster-id="clusterId"
          :disabled="editDisabled" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { BackupLogRecord } from '@services/source/fixpointRollback';

  import { useTimeZoneFormat } from '@hooks';

  import TableEditDateTime from '@components/render-table/columns/DateTime.vue';
  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  import { backupTypeList, BackupTypes } from '../../../../const';

  import RecordSelector from './RecordSelector.vue';

  interface Props {
    clusterId: number;
    backupid?: string;
    backupSource?: string;
    rollbackTime?: string;
  }

  interface Exposes {
    getValue: () => Promise<{
      backupinfo?: BackupLogRecord;
      rollback_time?: string;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { format: formatDateToUTC } = useTimeZoneFormat();

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('不能为空'),
    },
  ];

  const localRollbackTimeRef = ref<InstanceType<typeof TableEditDateTime>>();
  const localBackupFileRef = ref<InstanceType<typeof RecordSelector>>();
  const localBackupType = ref(BackupTypes.BACKUPID);
  const localRollbackTime = ref('');

  const editDisabled = computed(() => !props.clusterId || !props.backupSource);

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const hanldeBackupTypeChange = () => {
    localRollbackTime.value = '';
  };

  watch(
    () => props.rollbackTime,
    (newVal) => {
      if (newVal) {
        localBackupType.value = BackupTypes.TIME;
        localRollbackTime.value = newVal;
      } else {
        localBackupType.value = BackupTypes.BACKUPID;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.backupid,
    (newVal) => {
      if (newVal) {
        localBackupType.value = BackupTypes.BACKUPID;
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      if (localBackupType.value === BackupTypes.BACKUPID) {
        return localBackupFileRef.value!.getValue().then((data: BackupLogRecord) => ({
          rollback_type: `${props.backupSource?.toLocaleUpperCase()}_AND_${localBackupType.value}`,
          backupinfo: data,
        }));
      }
      return localRollbackTimeRef.value!.getValue().then(() => ({
        rollback_type: `${props.backupSource?.toLocaleUpperCase()}_AND_${localBackupType.value}`,
        rollback_time: formatDateToUTC(localRollbackTime.value),
      }));
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
