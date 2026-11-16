<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <DbDialog
    ref="dialog"
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="global-batch-config-dialog"
    :close-icon="false"
    :draggable="false"
    :quick-close="false"
    :width="980">
    <div class="global-batch-layout">
      <div class="global-batch-left">
        <div class="global-batch-header">
          <span>{{ meta.title }}</span>
          <BkButton
            :aria-label="t('关闭')"
            class="batch-close-button"
            :disabled="isSubmitting"
            text
            @click="handleClose">
            <DbIcon type="close" />
          </BkButton>
        </div>
        <DbForm
          class="global-batch-form"
          form-type="vertical"
          :model="formData">
          <BkAlert
            class="mb-24"
            closable
            theme="warning"
            :title="meta.description" />
          <DbFormItem
            v-if="mode !== 'timeout'"
            :label="mode === 'approve' ? t('审批') : t('确认执行')"
            required>
            <BkRadioGroup
              v-model="formData.flowValue"
              class="batch-flow-options"
              :disabled="isSubmitting"
              @change="markChanged">
              <BkRadio :label="true">
                <div class="batch-option-name">{{ mode === 'approve' ? t('需审批') : t('需确认') }}</div>
                <div class="batch-option-hint">
                  {{
                    mode === 'approve'
                      ? t('单据提交后需经 DBA 审批，方可进入下一阶段')
                      : t('流转至「确认执行」步骤时挂起，需人工「确认执行」才可进入下一阶段')
                  }}
                </div>
              </BkRadio>
              <BkRadio :label="false">
                <div class="batch-option-name">{{ mode === 'approve' ? t('免审批') : t('免确认') }}</div>
                <div class="batch-option-hint">
                  {{
                    mode === 'approve'
                      ? t('单据提交后跳过 DBA 审批，直接进入下一阶段')
                      : t('跳过「确认执行」步骤，直接进入下一阶段')
                  }}
                </div>
              </BkRadio>
            </BkRadioGroup>
          </DbFormItem>
          <template v-else>
            <DbFormItem
              :label="t('状态')"
              required>
              <DbSelect
                v-model="formData.state"
                :clearable="false"
                :disabled="isSubmitting"
                :placeholder="t('请选择状态')"
                @change="handleStateChange">
                <DbOption
                  v-for="state in stateOptions"
                  :key="state.value"
                  :label="state.label"
                  :value="state.value" />
              </DbSelect>
            </DbFormItem>
            <DbFormItem
              :label="t('目标值')"
              required>
              <TimeoutConfig
                :key="formData.state"
                v-model="formData.timeout"
                :disabled="isSubmitting || !formData.state"
                @change="markChanged" />
            </DbFormItem>
          </template>
        </DbForm>
      </div>
      <div class="global-batch-impact">
        <BkAlert
          v-if="checkMessage"
          class="mb-16"
          theme="warning"
          :title="checkMessage" />
        <div
          v-if="mode === 'timeout' && formData.state"
          class="mb-8">
          {{ t('本次设置：n', { n: stateOptions.find((state) => state.value === formData.state)?.label }) }}
        </div>
        <div class="batch-selection-summary">
          <I18nT
            keypath="已选单据类型：共 n 个"
            scope="global"
            tag="span">
            <template #n>
              <span class="batch-selection-count">{{ rows.length }}</span>
            </template>
          </I18nT>
          <template v-if="isChecked">
            <I18nT
              keypath="，设置 n，跳过 m"
              scope="global"
              tag="span">
              <template #n>
                <span class="batch-selection-count">{{ submitRows.length }}</span>
              </template>
              <template #m>
                <span class="batch-selection-count">{{ rows.length - submitRows.length }}</span>
              </template>
            </I18nT>
            <span v-if="reasonSummary">（{{ reasonSummary }}）</span>
          </template>
        </div>
        <div
          v-for="item in impact"
          :key="item.row.id"
          class="batch-impact-item"
          :class="{ 'is-skipped': isChecked && item.reason }">
          <span class="batch-impact-name">{{ item.row.ticket_type_display }}</span>
          <DbTag :theme="!isChecked ? 'info' : item.reason ? '' : 'success'">
            {{ !isChecked ? t('待设置') : item.reason ? t('跳过') : t('设置') }}
          </DbTag>
        </div>
      </div>
    </div>
    <template #footer>
      <BkButton
        v-bk-tooltips="{ content: t('无可设置项或输入校验不通过'), disabled: isChecked && submitRows.length > 0 }"
        class="w-88 mr-8"
        :disabled="!isChecked || !submitRows.length || isSubmitting"
        :loading="isSubmitting || (isValid && !checkResult && !checkFailed)"
        theme="primary"
        @click="handleConfirm">
        {{ t('设置') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="isShow = false">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbDialog>
</template>

<script setup lang="ts">
  import { I18nT, useI18n } from 'vue-i18n';

  import type TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import type { ExpireType } from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { checkUpdateTicketFlowConfig, updateTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { markSourceChanged, messageSuccess, releaseSourceChanged } from '@utils';

  import TimeoutConfig from './TimeoutConfig.vue';

  export type BatchMode = 'approve' | 'confirm' | 'timeout';

  interface Props {
    mode: BatchMode;
    rows: TicketFlowDescribeModel[];
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const beforeClose = useBeforeClose();
  const dialogRef = useTemplateRef('dialog');
  const changeSource = Symbol('global-batch-config');
  const dirty = ref(false);
  const isSubmitting = ref(false);
  const formData = reactive({
    flowValue: undefined as boolean | undefined,
    state: '' as ExpireType | '',
    timeout: undefined as number | undefined,
  });

  const meta = computed(
    () =>
      ({
        approve: {
          description: t(
            '为选中单据类型设置审批，仅更新流程控制方式为「平台设置」且审批值发生变化的单据类型，其他跳过',
          ),
          title: t('批量设置审批'),
        },
        confirm: {
          description: t(
            '为选中单据类型设置确认执行，仅更新流程控制方式为「平台设置」且确认值发生变化的单据类型，其他跳过',
          ),
          title: t('批量设置确认执行'),
        },
        timeout: {
          description: t(
            '为选中单据类型设置指定等待状态的超时规则，仅更新该状态适用、当前生效且超时值发生变化的单据类型，其他跳过',
          ),
          title: t('批量设置超时'),
        },
      })[props.mode],
  );
  const flowKey = computed(() => (props.mode === 'approve' ? 'need_itsm' : 'need_manual_confirm'));
  const stateOptions = computed(() => {
    const states = new Map<ExpireType, { label: string; value: ExpireType }>();
    props.rows.forEach((row) => row.orderedExpireTypes.forEach((state) => states.set(state.value, state)));
    return [...states.values()];
  });
  const isValid = computed(() => {
    if (props.mode !== 'timeout') return formData.flowValue !== undefined;
    return (
      Boolean(formData.state) &&
      (formData.timeout === -1 ||
        (formData.timeout !== undefined &&
          Number.isInteger(formData.timeout) &&
          formData.timeout >= 1 &&
          formData.timeout <= 2160))
    );
  });

  const checkResult = shallowRef<Awaited<ReturnType<typeof checkUpdateTicketFlowConfig>>>();
  const checkFailed = ref(false);
  const request = computed(() => {
    if (!isShow.value || !isValid.value) return undefined;
    const configs: Parameters<typeof updateTicketFlowConfig>[0]['configs'] = {};
    if (props.mode === 'timeout' && formData.state) configs.expire_config = { [formData.state]: formData.timeout };
    else configs[flowKey.value] = formData.flowValue;
    return {
      bk_biz_id: 0 as const,
      config_ids: props.rows.map((row) => row.id),
      configs,
      ticket_types: props.rows.map((row) => row.ticket_type),
    };
  });
  const checkMessage = computed(() => {
    const result = checkResult.value;
    if (result?.missing_config_ids.length || result?.missing_ticket_types.length)
      return t('页面信息不完整，请刷新页面后重试');
    const error = result?.config_errors
      .flatMap((item) => item.errors)
      .find((item) => !['inactive', 'not_applicable', 'preset', 'unchanged'].includes(item.code));
    if (error) return error.message || error.code_display || t('无可设置项或输入校验不通过');
    return checkFailed.value || (result && !result.valid && !result.config_errors.length)
      ? t('无可设置项或输入校验不通过')
      : '';
  });
  const isChecked = computed(() => isValid.value && Boolean(checkResult.value) && !checkMessage.value);
  const impact = computed(() =>
    props.rows.map((row) => {
      const errors = checkResult.value?.config_errors.find((item) => item.config_id === row.id)?.errors;
      // 每项仅计一个原因，控制边界与适用性优先于无变更。
      const error = errors?.find((item) => item.code !== 'unchanged') || errors?.[0];
      return { reason: error?.code_display || error?.message || '', row };
    }),
  );
  const submitRows = computed(() =>
    isChecked.value ? impact.value.filter((item) => !item.reason).map((item) => item.row) : [],
  );
  const reasonSummary = computed(() => {
    const counts = new Map<string, number>();
    impact.value.forEach((item) => {
      if (item.reason) counts.set(item.reason, (counts.get(item.reason) || 0) + 1);
    });
    return [...counts].map(([reason, count]) => `${reason} ${count}`).join('，');
  });

  watch(
    isShow,
    (value) => {
      if (value) {
        dirty.value = false;
        formData.flowValue = undefined;
        formData.state = '';
        formData.timeout = undefined;
      } else {
        releaseSourceChanged(changeSource);
      }
    },
    { flush: 'sync' },
  );

  watch(
    request,
    async (params, _previous, onCleanup) => {
      let current = true;
      onCleanup(() => {
        current = false;
      });
      checkResult.value = undefined;
      checkFailed.value = false;
      if (!params) return;
      try {
        const result = await checkUpdateTicketFlowConfig(params);
        if (current) checkResult.value = result;
      } catch {
        if (current) checkFailed.value = true;
      }
    },
    { flush: 'sync' },
  );

  const markChanged = () => {
    dirty.value = true;
    markSourceChanged(changeSource, true);
  };
  const handleStateChange = () => {
    formData.timeout = undefined;
    markChanged();
  };
  const handleBeforeClose = () => (isSubmitting.value ? false : beforeClose(dirty.value));
  const handleClose = async () => {
    if (await dialogRef.value!.beforeClose()) isShow.value = false;
  };

  const handleConfirm = async () => {
    if (!request.value || !submitRows.value.length || isSubmitting.value) return;
    const params = {
      ...request.value,
      config_ids: submitRows.value.map((row) => row.id),
      ticket_types: submitRows.value.map((row) => row.ticket_type),
    };
    isSubmitting.value = true;
    try {
      // 保存前重新检查设置项；检查与保存使用同一份入参。
      const result = await checkUpdateTicketFlowConfig(params);
      if (
        !result.valid ||
        result.config_errors.length ||
        result.missing_config_ids.length ||
        result.missing_ticket_types.length
      ) {
        checkResult.value = {
          ...result,
          config_errors: [...(checkResult.value?.config_errors || []), ...result.config_errors],
        };
        checkFailed.value = !result.valid && !result.config_errors.length;
        return;
      }
      await updateTicketFlowConfig(params);
      messageSuccess(t('操作成功'));
      isShow.value = false;
      emits('success');
    } finally {
      isSubmitting.value = false;
    }
  };

  onUnmounted(() => releaseSourceChanged(changeSource));
</script>

<style lang="less" scoped>
  .global-batch-config-dialog {
    :deep(.bk-modal-wrapper) {
      display: flex;
      max-width: calc(100vw - 48px);
      height: 560px;
      max-height: calc(100vh - 64px);
      flex-direction: column;
    }

    :deep(.bk-modal-body) {
      display: flex;
      flex: 1;
      min-height: 0;
      flex-direction: column;
    }

    :deep(.bk-modal-header) {
      display: none;
    }

    :deep(.bk-modal-content) {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    :deep(.bk-modal-content > div),
    :deep(.bk-dialog-content) {
      height: 100%;
    }

    :deep(.bk-dialog-content) {
      padding: 0;
      margin: 0;
      overflow: hidden;
    }

    :deep(.bk-dialog-footer) {
      flex-shrink: 0;
      padding: 12px 24px;
      background: #fff;
    }
  }

  .global-batch-layout {
    display: grid;
    height: 100%;
    min-height: 0;
    font-size: 12px;
    grid-template-columns: minmax(0, 1fr) 460px;

    .global-batch-left {
      display: flex;
      min-width: 0;
      min-height: 0;
      flex-direction: column;
    }

    .global-batch-header {
      display: flex;
      flex-shrink: 0;
      padding: 16px 20px 12px;
      font-size: 16px;
      font-weight: 500;
      color: #313238;
      border-bottom: 1px solid #dcdee5;
      align-items: center;
      justify-content: space-between;
    }

    .batch-close-button {
      color: #979ba5;
    }

    .global-batch-form {
      flex: 1;
      min-height: 0;
      padding: 12px 20px;
      overflow-y: auto;
    }

    .batch-flow-options {
      display: flex;
      align-items: stretch;
      flex-direction: column;
      gap: 12px;

      :deep(.bk-radio) {
        margin-left: 0;
        align-items: flex-start;
      }

      :deep(.bk-radio-input) {
        flex-shrink: 0;
        margin-top: 3px;
      }

      :deep(.bk-radio-label) {
        display: flex;
        min-width: 0;
        margin-left: 8px;
        flex-direction: column;
        gap: 3px;
        white-space: normal;
      }
    }

    .batch-option-name {
      line-height: 20px;
      color: #313238;
    }

    .batch-option-hint {
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
    }

    .global-batch-impact {
      min-width: 0;
      padding: 12px 20px;
      overflow-y: auto;
      background: #f5f7fa;
      border-left: 1px solid #dcdee5;
    }

    .batch-selection-summary {
      margin-bottom: 10px;
      line-height: 20px;
      color: #63656e;
    }

    .batch-selection-count {
      font-weight: 500;
      color: #3a84ff;
    }

    .batch-impact-item {
      display: flex;
      padding: 8px 0;
      border-bottom: 1px solid #f0f1f5;
      align-items: center;
      gap: 8px;

      &:last-child {
        border-bottom: 0;
      }

      &.is-skipped .batch-impact-name {
        color: #c4c6cc;
      }
    }

    .batch-impact-name {
      flex: 1;
      min-width: 0;
      font-weight: 500;
      color: #313238;
      overflow-wrap: anywhere;
    }
  }
</style>
