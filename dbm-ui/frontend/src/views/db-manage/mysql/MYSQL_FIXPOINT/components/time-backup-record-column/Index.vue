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
    :disabled-method="disabledMethod"
    field="backupTime"
    :label="t('指定时间')"
    :min-width="240"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('指定时间')"
        title-prefix-type="select"
        @change="handleBatchEdit">
        <template #content>
          <BkForm
            form-type="vertical"
            :model="formData">
            <BkFormItem
              field="backup_time"
              :label="t('指定时间（提交后自动选择与指定时间最近的全备记录文件）')"
              required>
              <BkDatePicker
                v-model="formData.backup_time"
                :clearable="false"
                :disabled-date="disableDate"
                :placeholder="t('请选择指定时间')"
                style="width: 360px"
                type="datetime" />
            </BkFormItem>
          </BkForm>
        </template>
      </BatchEditColumn>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-select"
        @click="handleShowBatchEdit">
        <DbIcon type="bulk-edit" />
      </span>
    </template>
    <EditableDatePicker
      v-model="backupTime"
      :disabled-date="disableDate"
      :placeholder="t('请选择指定时间')"
      type="datetime"
      @change="handleDateChange">
    </EditableDatePicker>
  </EditableColumn>
  <EditableColumn
    field="backupRecord"
    :label="t('备份记录')"
    :min-width="300"
    required>
    <EditableBlock
      :placeholder="t('自动生成')"
      style="width: 100%"
      @click="handleShowSelector">
      <div
        v-if="backupRecord.backup_id"
        class="content-block">
        <div class="content-label">{{ t('备份文件名：') }}</div>
        <div class="content-value">{{ `${backupRecord.mysql_role} ${utcDisplayTime(backupRecord.backup_time)}` }}</div>
        <div class="content-label">{{ t('备份范围：') }}</div>
        <div class="content-value">{{ backupRecord.is_full_backup === '1' ? t('全库备份') : t('库表备份') }}</div>
        <div class="content-label">{{ t('备份类型：') }}</div>
        <div class="content-value">{{ backupRecord.backup_type === 'logical' ? t('逻辑备份') : t('物理备份') }}</div>
        <div class="content-label">{{ t('发起方式：') }}</div>
        <div class="content-value">{{ backupRecord.bill_id ? t('单据备份') : t('例行备份') }}</div>
        <div class="content-label">{{ t('文件大小：') }}</div>
        <div class="content-value">{{ bytePretty(backupRecord.extra_fields?.total_filesize ?? 0) }}</div>
        <div
          v-if="backupRecord.bill_id"
          class="content-label">
          {{ t('关联单据：') }}
        </div>
        <div
          v-if="backupRecord.bill_id"
          class="content-value">
          <RouterLink
            v-if="backupRecord.bill_id"
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: backupRecord.bill_id,
              },
            }">
            {{ backupRecord.bill_id }}
          </RouterLink>
          <span v-else>--</span>
        </div>
      </div>
    </EditableBlock>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { type BackupLogRecord, queryLatesBackupLog } from '@services/source/fixpointRollback';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  interface Props {
    backupSource: 'local' | 'remote';
    cluster: TendbhaModel;
  }

  type Emits = (e: 'batch-edit', data: typeof backupTime.value | typeof backupRecord.value, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const backupTime = defineModel<string>('backupTime', {
    required: true,
  });

  const backupRecord = defineModel<BackupLogRecord>('backupRecord', {
    required: true,
  });

  const { t } = useI18n();

  const isShowSelector = ref(false);
  const isShowBatchEdit = ref(false);
  const formData = ref({
    backup_time: '',
  });

  const { run: fetchData } = useRequest(queryLatesBackupLog, {
    manual: true,
    onSuccess(data) {
      backupRecord.value = data;
    },
  });

  const disabledMethod = () => (props.cluster.id ? false : t('请先选择集群'));
  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleDateChange = (date: string) => {
    backupTime.value = date;
    fetchData({
      backup_source: props.backupSource,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.cluster.id,
      rollback_time: date,
    });
  };

  const handleBatchEdit = async () => {
    const data = await queryLatesBackupLog({
      backup_source: props.backupSource,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.cluster.id,
      rollback_time: formData.value.backup_time,
    });
    emits('batch-edit', formData.value.backup_time, 'backupTime');
    emits('batch-edit', data, 'backupRecord');
  };
</script>
<style lang="less" scoped>
  .batch-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .content-block {
    display: grid;
    grid-template-columns: 0fr 1fr;

    .content-label {
      width: 80px;
      text-align: right;
    }

    .content-value {
      width: 200px;
    }
  }
</style>
