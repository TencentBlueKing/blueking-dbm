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
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="backupRecord.backup_identify"
    :label="t('备份记录')"
    :min-width="260"
    required
    :tooltip="
      t(
        '一条备份记录包含一次备份中该集群各分片的全备。在选择器内选择备份记录与构造范围；TendisSSD / TendisPlus 有 binlog，还可设置构造到的时间点',
      )
    ">
    <div
      v-if="modelValue"
      class="backup-record-cell"
      @click="emit('open')">
      <div class="backup-rec">
        <div class="backup-rec-label">{{ t('备份记录') }}：</div>
        <div class="backup-rec-value is-identify">{{ modelValue.backup_identify }}</div>
        <div class="backup-rec-label">{{ t('备份方式') }}：</div>
        <div class="backup-rec-value">{{ backupTypeText }}</div>
        <div class="backup-rec-label">{{ t('构造范围') }}：</div>
        <div class="backup-rec-value">{{ scopeText }}</div>
        <template v-if="showRecovery">
          <div class="backup-rec-label">{{ t('构造到') }}：</div>
          <div class="backup-rec-value">{{ modelValue.recovery_time_point || t('仅用全备') }}</div>
        </template>
        <template v-if="modelValue.allow_binlog_nonconsecutive">
          <div class="backup-rec-label">{{ t('binlog 不连续') }}：</div>
          <div class="backup-rec-value">{{ t('仍构造') }}</div>
        </template>
      </div>
      <div
        v-if="precheckText || topoWarning"
        class="backup-rec-foot">
        <span
          v-if="precheckText"
          :class="precheckClass">
          {{ precheckText }}
        </span>
        <span
          v-if="topoWarning"
          v-bk-tooltips="topoWarning"
          class="topo-tip ml-4">
          <DbIcon type="gaojing" />
        </span>
      </div>
    </div>
    <EditableBlock
      v-else
      class="backup-record-empty"
      :placeholder="t('点击选择')"
      @click="emit('open')" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    getBackupTypeText,
    getScopeText,
    hasBinlog,
    type IBackupRecord,
    type IPrecheckResult,
    type PrecheckState,
  } from './backup-record';

  interface Props {
    clusterId: number;
    clusterType: string;
    precheck?: IPrecheckResult;
  }

  type Emits = (e: 'open') => void;

  const props = defineProps<Props>();

  const emit = defineEmits<Emits>();

  const modelValue = defineModel<IBackupRecord | null>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('请选择备份记录'),
      trigger: 'change',
      validator: (value: string) => Boolean(value),
    },
    {
      // 预校验不通过的行不允许提交，随列校验报错
      message: t('预校验不通过'),
      trigger: 'change',
      validator: () => props.precheck?.state !== 'fail',
    },
  ];

  // 未填写待构造的集群时禁用并提示
  const disabledMethod = () => (props.clusterId ? false : t('请先选择待构造的集群'));

  const backupTypeText = computed(() => (modelValue.value ? getBackupTypeText(modelValue.value.backup_identify) : ''));

  const scopeText = computed(() => (modelValue.value ? getScopeText(modelValue.value) : ''));

  const showRecovery = computed(() => Boolean(modelValue.value) && hasBinlog(props.clusterType));

  const topoWarning = computed(() => {
    if (!modelValue.value || !modelValue.value.current_shard_count) {
      return '';
    }
    return modelValue.value.shard_count !== modelValue.value.current_shard_count
      ? t('备份时 x 个分片，当前 y 个分片，将按备份时的分片构造', {
          x: modelValue.value.shard_count,
          y: modelValue.value.current_shard_count,
        })
      : '';
  });

  const precheckClass = computed(() => {
    if (!props.precheck) {
      return '';
    }
    const classMap: Partial<Record<PrecheckState, string>> = {
      fail: 'is-error',
      pass: 'is-success',
      warning: 'is-warning',
    };
    return classMap[props.precheck.state] || '';
  });

  const precheckText = computed(() => {
    if (!props.precheck || props.precheck.state === 'unset') {
      return '';
    }
    const { message, state } = props.precheck;
    if (state === 'fail') {
      return t('预校验不通过：n', { n: message });
    }
    if (state === 'warning') {
      return t('预校验通过：n', { n: message });
    }
    return t('预校验通过');
  });
</script>

<style lang="less" scoped>
  .backup-record-cell {
    padding: 0 8px;
    cursor: pointer;

    &:hover {
      background: #f5f7fa;
    }
  }

  // 「标签 ：值」双列回显（标签右对齐）
  .backup-rec {
    display: grid;
    grid-template-columns: max-content 1fr;
    column-gap: 4px;
    font-size: 12px;
    line-height: 22px;
    color: #313238;

    .backup-rec-label {
      color: #63656e;
      text-align: right;
      white-space: nowrap;
    }

    .backup-rec-value {
      white-space: nowrap;

      &.is-identify {
        font-weight: 500;
      }
    }
  }

  .backup-rec-foot {
    margin-top: 4px;
    font-size: 12px;

    .is-success {
      color: #2dcb56;
    }

    .is-warning {
      color: #eb9000;
    }

    .is-error {
      color: #ea3636;
    }

    .topo-tip {
      color: #eb9000;
    }
  }

  // 空态块与已选态保持一致的可点击反馈
  .backup-record-empty {
    cursor: pointer;

    &:hover {
      background: #f5f7fa;
    }
  }
</style>
