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
  <DbSideslider
    ref="sideslider"
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    quick-close
    :width="960">
    <template #header>
      <div class="global-config-header">
        <span>{{ t('单据设置') }}</span>
        <div class="split-line" />
        <div class="ticket-type-display">{{ data.ticket_type_display }}</div>
      </div>
    </template>
    <DbForm
      class="global-config-form"
      form-type="vertical"
      :model="formData">
      <h3>{{ t('审批与确认执行') }}</h3>
      <div class="global-config-group">
        <DbFormItem
          v-for="field in flowFields"
          :key="field.key"
          :label="field.label">
          <template v-if="data[`editable_${field.key}`] === true">
            <BkSwitcher
              v-model="formData[field.key]"
              theme="primary"
              @change="handleFlowChange(field.key)" />
            <span class="ml-8">{{ flowValueText(field.key) }}</span>
            <span class="config-hint ml-8">{{ formData[field.key] ? field.onHint : field.offHint }}</span>
          </template>
          <template v-else>
            <span>{{ data[`editable_${field.key}`] === null ? t('逐单判定') : flowValueText(field.key) }}</span>
            <DbIcon
              class="ml-4"
              type="lock-fill" />
            <span class="config-hint ml-8">
              {{
                data[`editable_${field.key}`] === null
                  ? t('由该单据在提交时按提单内容判定，不受本页设置影响')
                  : t('由该单据流程预先确定，不受本页设置影响')
              }}
            </span>
          </template>
        </DbFormItem>
      </div>
      <h3>
        {{ t('超时自动终止') }}
        <span class="config-hint ml-8">{{ t('各状态分别设置 · 自定义范围 1～2160 小时') }}</span>
      </h3>
      <div
        v-if="visibleStates.length"
        class="global-timeout-list">
        <div
          v-for="state in visibleStates"
          :key="state.value"
          class="global-timeout-row">
          <span class="global-timeout-label">{{ state.label }}</span>
          <TimeoutConfig
            v-model="formData.expire_config[state.value]"
            @change="handleTimeoutChange(state.value)" />
        </div>
      </div>
      <div v-else>--</div>
    </DbForm>
    <template #footer>
      <BkButton
        v-bk-tooltips="{ content: t('当前无变更，请先修改内容'), disabled: dirty }"
        class="w-88 mr-8"
        :disabled="!dirty || !isValid"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSave">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88"
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import type { ExpireType } from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { updateTicketFlowConfig } from '@services/source/ticket';

  import { useBeforeClose } from '@hooks';

  import { markSourceChanged, messageSuccess, releaseSourceChanged } from '@utils';

  import TimeoutConfig from './TimeoutConfig.vue';

  interface Props {
    data: TicketFlowDescribeModel;
  }

  type Emits = (e: 'success') => void;
  type FlowKey = 'need_itsm' | 'need_manual_confirm';

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const beforeClose = useBeforeClose();
  const sidesliderRef = useTemplateRef('sideslider');
  const flowFields: { key: FlowKey; label: string; offHint: string; onHint: string }[] = [
    {
      key: 'need_itsm',
      label: t('审批'),
      offHint: t('单据提交后跳过 DBA 审批，直接进入下一阶段'),
      onHint: t('单据提交后需经 DBA 审批，方可进入下一阶段'),
    },
    {
      key: 'need_manual_confirm',
      label: t('确认执行'),
      offHint: t('跳过「确认执行」步骤，直接进入下一阶段'),
      onHint: t('流转至「确认执行」步骤时挂起，需人工「确认执行」才可进入下一阶段'),
    },
  ];
  const changeSource = Symbol('global-ticket-config');
  const dirty = ref(false);
  const isSubmitting = ref(false);
  const changedFlowKeys = new Set<FlowKey>();
  const changedTimeoutKeys = new Set<ExpireType>();
  const formData = reactive({
    expire_config: {} as Partial<Record<ExpireType, number | undefined>>,
    need_itsm: false,
    need_manual_confirm: false,
  });

  const flowValueText = (key: FlowKey) =>
    key === 'need_itsm' ? (formData[key] ? t('需审批') : t('免审批')) : formData[key] ? t('需确认') : t('免确认');
  const visibleStates = computed(() =>
    props.data.orderedExpireTypes.filter(
      (state) =>
        state.value !== 'pause' || props.data.editable_need_manual_confirm !== true || formData.need_manual_confirm,
    ),
  );
  const isValid = computed(() =>
    visibleStates.value.every((state) => {
      const value = formData.expire_config[state.value];
      return value === -1 || (value !== undefined && Number.isInteger(value) && value >= 1 && value <= 2160);
    }),
  );

  watch(isShow, (value) => {
    if (value) {
      dirty.value = false;
      changedFlowKeys.clear();
      changedTimeoutKeys.clear();
      formData.need_itsm = props.data.configs.need_itsm;
      formData.need_manual_confirm = props.data.configs.need_manual_confirm;
      formData.expire_config = Object.fromEntries(
        props.data.supported_expire_types.map((state) => [
          state.value,
          props.data.configs.expire_config?.[state.value] ?? -1,
        ]),
      );
    } else {
      releaseSourceChanged(changeSource);
    }
  });

  const markChanged = () => {
    dirty.value = true;
    markSourceChanged(changeSource, true);
  };
  const handleFlowChange = (key: FlowKey) => {
    changedFlowKeys.add(key);
    markChanged();
  };
  const handleTimeoutChange = (key: ExpireType) => {
    changedTimeoutKeys.add(key);
    markChanged();
  };
  const handleBeforeClose = () => (isSubmitting.value ? false : beforeClose(dirty.value));

  const handleSave = async () => {
    if (!dirty.value || !isValid.value || isSubmitting.value) return;
    const configs: Parameters<typeof updateTicketFlowConfig>[0]['configs'] = {};
    changedFlowKeys.forEach((key) => {
      if (props.data[`editable_${key}`] === true) configs[key] = formData[key];
    });
    // 仅提交操作过且当前生效的状态，免确认时保留后端原有待执行配置。
    const expireConfig: NonNullable<typeof configs.expire_config> = {};
    visibleStates.value.forEach((state) => {
      if (changedTimeoutKeys.has(state.value)) {
        expireConfig[state.value] = formData.expire_config[state.value];
      }
    });
    if (Object.keys(expireConfig).length) configs.expire_config = expireConfig;

    isSubmitting.value = true;
    try {
      await updateTicketFlowConfig({
        bk_biz_id: 0,
        cluster_ids: [],
        config_ids: [props.data.id],
        configs,
        ticket_types: [props.data.ticket_type],
      });
      messageSuccess(t('保存成功'));
      isShow.value = false;
      emits('success');
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleCancel = async () => {
    if (await sidesliderRef.value!.beforeClose()) isShow.value = false;
  };

  onUnmounted(() => releaseSourceChanged(changeSource));
</script>

<style lang="less" scoped>
  .global-config-header {
    display: flex;
    align-items: center;

    .split-line {
      width: 1px;
      height: 14px;
      margin: 0 8px;
      background-color: #dcdee5;
    }

    .ticket-type-display {
      font-size: 14px;
      color: #979ba5;
    }
  }

  .global-config-form {
    padding: 24px;

    h3 {
      margin: 0 0 16px;
      font-size: 14px;
      color: #313238;
    }

    .config-hint {
      font-size: 12px;
      font-weight: normal;
      color: #979ba5;
    }

    .global-config-group {
      padding: 16px;
      margin-bottom: 24px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
    }

    .global-timeout-list {
      border: 1px solid #dcdee5;
      border-radius: 2px;
    }

    .global-timeout-row {
      display: flex;
      min-height: 52px;
      padding: 8px 16px;
      align-items: center;
      border-bottom: 1px solid #f0f1f5;

      &:last-child {
        border-bottom: 0;
      }
    }

    .global-timeout-label {
      width: 100px;
      flex-shrink: 0;
    }
  }
</style>
