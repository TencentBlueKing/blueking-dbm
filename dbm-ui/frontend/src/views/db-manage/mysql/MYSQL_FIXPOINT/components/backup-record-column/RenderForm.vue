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
  <div class="backup-type-is-time">
    <div class="backup-type-is-time-block">
      <div class="align-center">
        <DbIcon type="bk-dbm-icon db-icon-attention" />
        <div class="backup-type-is-time-text ml-5">{{ t('根据“指定日期”前自动匹配制定日期前的最新的备份') }}</div>
      </div>
      <BkForm
        ref="formRef"
        class="backup-type-is-time-form"
        :model="formData">
        <BkFormItem
          field="backup_time"
          :label="t('指定时间')"
          required>
          <BkDatePicker
            v-model="formData.backup_time"
            append-to-body
            :clearable="false"
            :disabled-date="disableDate"
            :placeholder="t('请选择')"
            style="width: 240px"
            type="datetime" />
        </BkFormItem>
        <BkFormItem
          field="backup_type"
          :label="t('备份范围')"
          required>
          <BkRadioGroup
            v-model="formData.backup_type"
            class="mb-12"
            style="width: 100%">
            <BkRadio :label="BACKUP_TYPE.ALL">
              {{ t('全部') }}
            </BkRadio>
            <BkRadio :label="BACKUP_TYPE.FULL">
              {{ t('仅全库备份') }}
            </BkRadio>
            <BkRadio :label="BACKUP_TYPE.DB_TABLE">
              {{ t('仅全库备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
      </BkForm>
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { type BackupLogRecord, queryLatesBackupLog } from '@services/source/fixpointRollback';

  interface Props {
    backupSource: 'local' | 'remote';
    cluster: TendbhaModel;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<BackupLogRecord>();

  const { t } = useI18n();

  enum BACKUP_TYPE {
    ALL = 'all_backup',
    DB_TABLE = 'db_table_backup',
    FULL = 'full_backup',
  }

  const formRef = ref();
  const formData = ref({
    backup_time: '',
    backup_type: BACKUP_TYPE.ALL,
  });

  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const { run: fetchData } = useRequest(queryLatesBackupLog, {
    manual: true,
    onSuccess(data) {
      modelValue.value = data;
    },
  });

  watch(
    formData,
    async () => {
      const valid = await formRef.value.validate();
      if (!valid) {
        return;
      }
      fetchData({
        backup_source: props.backupSource,
        backup_type: formData.value.backup_type,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_id: props.cluster.id,
        rollback_time: formData.value.backup_time,
      });
    },
    {
      deep: true,
    },
  );
</script>
