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
    field="backupRecord"
    :label="t('备份记录')"
    :min-width="300"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="t('备份记录')"
        :width="504"
        title-prefix-type="select"
        @change="handleBatchEdit">
        <template #content>
          <BkForm
            form-type="vertical"
            :model="formData">
            <BkFormItem
              field="backup_time"
              :label="t('备份文件（批量编辑仅支持“指定时间自动匹配”）')"
              required>
              <BkDatePicker
                v-model="formData.backup_time"
                :clearable="false"
                :disabled-date="disableDate"
                :placeholder="t('请选择')"
                style="width: 360px"
                type="datetime" />
            </BkFormItem>
            <BkFormItem
              field="backup_method"
              :label="t('备份范围')"
              required>
              <BkRadioGroup
                v-model="formData.backup_method"
                class="mb-12"
                style="width: 100%">
                <BkRadio label="all">
                  {{ t('全部') }}
                </BkRadio>
                <BkRadio :label="BackupMethod.full_by_ticket">
                  {{ t('全库备份（单据）') }}
                </BkRadio>
                <BkRadio :label="BackupMethod.partial_by_ticket">
                  {{ t('库表备份（单据）') }}
                </BkRadio>
                <BkRadio :label="BackupMethod.full_by_regular">
                  {{ t('全库备份（例行）') }}
                </BkRadio>
              </BkRadioGroup>
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
    <EditableBlock
      v-if="modelValue.backup_id"
      style="width: 100%"
      @click="handleShowSelector">
      <div class="content-block">
        <div class="content-label">{{ t('备份文件名：') }}</div>
        <div class="content-value">{{ `${modelValue.mysql_role} ${utcDisplayTime(modelValue.backup_time)}` }}</div>
        <div class="content-label">{{ t('备份范围：') }}</div>
        <div class="content-value">{{ backupMethodMap[modelValue.backup_method] || '--' }}</div>
        <div class="content-label">{{ t('备份类型：') }}</div>
        <div class="content-value">{{ backupTypeMap[modelValue.backup_type] || '--' }}</div>
        <div class="content-label">{{ t('文件大小：') }}</div>
        <div class="content-value">{{ bytePretty(modelValue?.total_filesize ?? 0) }}</div>
        <div
          v-if="modelValue.bill_id"
          class="content-label">
          {{ t('关联单据：') }}
        </div>
        <div
          v-if="modelValue.bill_id"
          class="content-value">
          <RouterLink
            v-if="modelValue.bill_id"
            target="_blank"
            :to="{
              name: 'ticketDetail',
              params: {
                ticketId: modelValue.bill_id,
              },
            }">
            {{ modelValue.bill_id }}
          </RouterLink>
          <span v-else>--</span>
        </div>
      </div>
    </EditableBlock>
    <EditableSelect
      v-else
      :popover-options="{
        boundary: 'parent',
        trigger: 'manual',
        isShow: false,
      }"
      @click="handleShowSelector" />
  </EditableColumn>
  <BackupRecordSelector
    v-model="modelValue"
    v-model:is-show="isShowSelector"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { type BackupLogRecord, queryLatesBackupLog } from '@services/source/fixpointRollback';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import { bytePretty, utcDisplayTime } from '@utils';

  import BackupRecordSelector from '../backup-record-selector/Index.vue';

  interface Props {
    backupSource: 'local' | 'remote';
    cluster: TendbhaModel;
  }

  interface Emits {
    (e: 'batch-edit', data: typeof modelValue.value, field: string): void;
    (e: 'change'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<BackupLogRecord>({
    required: true,
  });

  const { t } = useI18n();

  const isShowSelector = ref(false);
  const isShowBatchEdit = ref(false);
  enum BackupMethod {
    non_full_by_regular = 'non_full_by_regular',
    full_by_ticket = 'full_by_ticket',
    partial_by_ticket = 'partial_by_ticket',
    full_by_regular = 'full_by_regular',
  }

  const formData = ref({
    backup_time: '',
    backup_method: 'all',
  });

  const backupMethodMap = {
    full_by_ticket: t('全库备份（单据）'),
    partial_by_ticket: t('库表备份（单据）'),
    full_by_regular: t('全库备份（例行）'),
    non_full_by_regular: t('非全库备份（例行）'), // 过滤掉，不展示
  } as Record<string, string>;

  const backupTypeMap = {
    logical: t('逻辑备份'),
    physical: t('物理备份'),
  } as Record<string, string>;

  const disabledMethod = () => (props.cluster.id ? false : t('请先选择集群'));
  const disableDate = (date?: Date | number) => dayjs(date).isAfter(dayjs(), 'day');

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = async () => {
    const data = await queryLatesBackupLog({
      backup_source: props.backupSource,
      backup_method: formData.value.backup_method === 'all' ? undefined : formData.value.backup_method,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.cluster.id,
      rollback_time: dayjs(new Date(formData.value.backup_time)).format('YYYY-MM-DD HH:mm:ss'),
    });
    emits('batch-edit', data, 'backupRecord');
  };

  watch(modelValue, () => {
    emits('change');
  });
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
