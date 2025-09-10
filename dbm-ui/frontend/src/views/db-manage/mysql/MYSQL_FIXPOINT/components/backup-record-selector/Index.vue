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
  <BkDialog
    class="mysql-backup-record-selector"
    :close-icon="false"
    :draggable="false"
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="t('选择备份记录')"
    :width="dialogWidth"
    @closed="handleClose">
    <BkRadioGroup
      v-model="radioGroupValue"
      class="mb-12"
      style="width: 100%"
      type="capsule">
      <BkRadioButton
        :label="BACKUP_TYPE.MANUAL"
        style="flex: 1">
        {{ t('手动选择') }}
      </BkRadioButton>
      <BkRadioButton
        :label="BACKUP_TYPE.AUTO"
        style="flex: 1">
        {{ t('通过指定时间自动匹配') }}
      </BkRadioButton>
    </BkRadioGroup>
    <KeepAlive>
      <RenderTable
        v-if="radioGroupValue === BACKUP_TYPE.MANUAL"
        ref="tableRef"
        v-bind="props"
        v-model="localValue" />
      <RenderForm
        v-else
        v-model="localValue"
        v-bind="props" />
    </KeepAlive>
    <template #footer>
      <div class="mysql-backup-record-selector-footer">
        <div class="align-center">
          <div class="footer-text">{{ t('已选择：') }}</div>
          <div
            v-if="localValue?.backup_id"
            class="footer-text"
            style="font-weight: bold">
            {{ `${localValue?.mysql_role} ${utcDisplayTime(localValue?.backup_time)}` }}
          </div>
          <div v-else>--</div>
          <BkButton
            class="ml-8"
            text
            theme="primary"
            @click="handeClear">
            {{ t('清空') }}
          </BkButton>
        </div>
        <div class="align-center footer-btn">
          <BkButton
            class="cluster-selector-button mr-8"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            class="cluster-selector-button"
            @click="handleClose">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { type BackupLogRecord } from '@services/source/fixpointRollback';

  import { useSelectorDialogWidth } from '@hooks';

  import { utcDisplayTime } from '@utils';

  import RenderForm from './RenderForm.vue';
  import RenderTable from './RenderTable.vue';

  interface Props {
    backupSource: 'local' | 'remote';
    cluster: TendbhaModel;
    /**
     * 仅全备
     */
    onlyFull?: boolean;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const modelValue = defineModel<BackupLogRecord>();

  const localValue = ref<BackupLogRecord>();

  const { dialogWidth } = useSelectorDialogWidth();
  const { t } = useI18n();

  enum BACKUP_TYPE {
    MANUAL,
    AUTO,
  }
  const radioGroupValue = ref(BACKUP_TYPE.MANUAL);
  const tableRef = ref();

  const handeClear = () => {
    tableRef.value?.clear();
    localValue.value = undefined;
  };

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    modelValue.value = localValue.value;
    handleClose();
  };

  watch(isShow, () => {
    if (isShow.value) {
      localValue.value = modelValue.value;
      tableRef.value?.init();
    }
  });
</script>
<style lang="less">
  .mysql-backup-record-selector {
    .align-center {
      display: flex;
      align-items: center;
    }

    .backup-time-picker {
      display: flex;
      width: 71px;
      height: 32px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 12px;
      line-height: 20px;
      letter-spacing: 0;
      color: #4d4f56;
      background: #fafbfd;
      border: 1px solid #c4c6cc;
      border-right: none;
      border-radius: 2px 0 0 2px;
      align-items: center;
      justify-content: center;
    }

    .backup-type-is-time {
      height: 470px;

      .backup-type-is-time-block {
        position: relative;
        width: 100%;
        height: 153px;
        padding: 18px;
        background: #f5f7fa;

        .backup-type-is-time-text {
          display: flex;
          font-family: MicrosoftYaHei, sans-serif;
          font-size: 12px;
          letter-spacing: 0;
          color: #4d4f56;
          align-items: center;
        }

        .backup-type-is-time-form {
          position: absolute;
          top: 52px;
          left: -40px;
        }
      }
    }

    .mysql-backup-record-selector-footer {
      position: relative;
      display: flex;
      align-items: center;
      height: 40px;

      .footer-text {
        font-family: MicrosoftYaHei, sans-serif;
        font-size: 12px;
        line-height: 0;
        letter-spacing: 0;
        color: #4d4f56;
        text-align: left;
      }

      .footer-btn {
        position: absolute;
        right: 0;
      }
    }
  }
</style>
