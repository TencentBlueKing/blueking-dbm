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
  <BkSideslider
    :before-close="handleClose"
    :is-show="isShow"
    render-directive="if"
    :width="1110"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        {{ t('编辑策略') }}
        【
        <span class="name">{{ data.name }}</span>
        】
        <BkTag theme="info">
          {{ t('平台配置') }}
        </BkTag>
      </div>
    </template>
    <div class="edit-strategy-main-box">
      <BkForm
        ref="formRef"
        form-type="vertical"
        :model="formModel">
        <BkFormItem
          :label="t('策略名称')"
          required>
          <BkInput
            disabled
            :value="data.name" />
        </BkFormItem>
        <BkFormItem
          :label="t('监控目标')"
          required>
          <BkSelect
            v-model="monitorTarget"
            disabled />
        </BkFormItem>
        <BkFormItem
          :label="t('检测规则')"
          required>
          <div class="check-rules">
            <RuleCheck
              v-if="infoRule"
              ref="infoValueRef"
              :data="infoRule"
              :indicator="data.monitor_indicator"
              :title="t('提醒')">
              <DbIcon
                class="title-icon"
                type="attention-fill" />
            </RuleCheck>
            <RuleCheck
              v-if="warnRule"
              ref="warnValueRef"
              :data="warnRule"
              :indicator="data.monitor_indicator"
              :title="t('预警')">
              <DbIcon
                class="title-icon icon-warn"
                type="attention-fill" />
            </RuleCheck>
            <RuleCheck
              v-if="dangerRule"
              ref="dangerValueRef"
              :data="dangerRule"
              :indicator="data.monitor_indicator"
              :title="t('致命')">
              <DbIcon
                class="title-icon icon-dander"
                type="alert" />
            </RuleCheck>
          </div>
        </BkFormItem>
        <JudgingCondition
          v-model="formModel"
          :monitor-policy-id="data.monitor_policy_id" />
        <BkFormItem
          :label="t('告警通知')"
          property="notifyRules"
          required>
          <BkCheckboxGroup v-model="formModel.notifyRules">
            <BkCheckbox
              v-for="item in notifyTypes"
              :key="item.label"
              :label="item.value">
              {{ item.label }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('默认通知对象')"
          required>
          <BkSelect
            v-model="nofityTarget"
            class="notify-select"
            disabled
            multiple-mode="tag">
            <template #tag>
              <div class="notify-tag-box">
                <DbIcon
                  style="font-size: 16px"
                  type="auth" />
                <span class="dba">{{ nofityTarget }}</span>
                <DbIcon
                  class="close-icon"
                  type="close" />
              </div>
            </template>
          </BkSelect>
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="updateLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkPopConfirm
        :content="t('将会覆盖当前填写的内容，并恢复默认')"
        placement="top"
        trigger="click"
        width="280"
        @confirm="handleClickConfirmRecoverDefault">
        <BkButton
          class="mr-8"
          :disabled="updateLoading">
          {{ t('恢复默认') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton
        :disabled="updateLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { computed, type UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { updatePolicy } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import RuleCheck from '@components/monitor-rule-check/index.vue';

  import JudgingCondition from '@views/monitor-alarm/common/judging-condition/Index.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    data: MonitorPolicyModel;
    dbType: DBTypes;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const generateRule = (data: MonitorPolicyModel, level: number) => {
    const arr = data.test_rules.filter((item) => item.level === level);
    return arr.length > 0 ? arr[0] : undefined;
  };

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const infoValueRef = ref();
  const warnValueRef = ref();
  const dangerValueRef = ref();
  const monitorTarget = ref(t('全部业务'));
  const nofityTarget = ref(`{${DBTypeInfos[props.dbType].name}_DBA}`);
  const formRef = ref();
  const formModel = reactive({
    detectsConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['detectsConfig'],
    noDataConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['noDataConfig'],
    notifyRules: [] as string[],
  });

  const dangerRule = computed(() => generateRule(props.data, 1));
  const warnRule = computed(() => generateRule(props.data, 2));
  const infoRule = computed(() => generateRule(props.data, 3));

  const notifyTypes = [
    {
      label: t('告警时触发'),
      value: 'abnormal',
    },
    {
      label: t('告警恢复时'),
      value: 'recovered',
    },
    {
      label: t('告警关闭时'),
      value: 'closed',
    },
    {
      label: t('告警确认时'),
      value: 'ack',
    },
  ];

  const { loading: updateLoading, run: runUpdatePolicy } = useRequest(updatePolicy, {
    manual: true,
    onSuccess: (updateResult) => {
      if (updateResult.bkm_id) {
        messageSuccess(t('保存成功'));
        emits('success');
        isShow.value = false;
      }
    },
  });

  watch(
    () => props.data,
    (data) => {
      if (data.id) {
        formModel.notifyRules = _.cloneDeep(data.notify_rules);
        formModel.noDataConfig = _.cloneDeep(data.no_data_config);

        const detectsConfig = _.cloneDeep(data.detects_config) as unknown as UnwrapRef<
          typeof formModel
        >['detectsConfig'];
        detectsConfig.trigger_config.uptime.time_ranges = data.detects_config.trigger_config.uptime.time_ranges.map(
          (item) => [item.start, item.end] as [string, string],
        );
        formModel.detectsConfig = detectsConfig;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickConfirmRecoverDefault = () => {
    formModel.notifyRules = _.cloneDeep(props.data.notify_rules);
    formModel.noDataConfig = _.cloneDeep(props.data.no_data_config);

    const detectsConfig = _.cloneDeep(props.data.detects_config) as unknown as UnwrapRef<
      typeof formModel
    >['detectsConfig'];
    detectsConfig.trigger_config.uptime.time_ranges = props.data.detects_config.trigger_config.uptime.time_ranges.map(
      (item) => [item.start, item.end] as [string, string],
    );
    formModel.detectsConfig = detectsConfig;

    infoValueRef.value.resetValue();
    warnValueRef.value.resetValue();
    dangerValueRef.value.resetValue();
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();
    const testRules = [
      infoRule.value ? infoValueRef.value.getValue() : undefined,
      warnRule.value ? warnValueRef.value.getValue() : undefined,
      dangerRule.value ? dangerValueRef.value.getValue() : undefined,
    ];
    const detectsConfig = _.cloneDeep(formModel.detectsConfig) as unknown as MonitorPolicyModel['detects_config'];
    detectsConfig.trigger_config.uptime.time_ranges = formModel.detectsConfig.trigger_config.uptime.time_ranges.map(
      (item) => ({
        end: item[1],
        start: item[0],
      }),
    );
    const reqParams = {
      custom_conditions: props.data.custom_conditions,
      detects_config: detectsConfig,
      no_data_config: formModel.noDataConfig,
      notify_groups: props.data.notify_groups,
      notify_rules: formModel.notifyRules,
      targets: props.data.targets,
      test_rules: testRules.filter((item) => item && item.config.length !== 0),
    };
    runUpdatePolicy(props.data.id, reqParams);
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) {
      return false;
    }
    window.changeConfirm = false;
    isShow.value = false;
    return true;
  }
</script>

<style lang="less" scoped>
  .header-main {
    display: flex;
    width: 100%;
    overflow: hidden;
    align-items: center;

    .name {
      width: auto;
      max-width: 720px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .edit-strategy-main-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    :deep(.bk-form-label) {
      font-weight: bolder;
      color: #63656e;
    }

    .item-title {
      margin-bottom: 6px;
      font-weight: normal;
      color: #63656e;
    }

    .check-rules {
      display: flex;
      flex-direction: column;
      gap: 16px;

      .title-icon {
        display: flex;
        width: 24px;
        height: 24px;
        font-size: 16px;
        color: #3a84ff;
        background-color: #f0f5ff;
        border: none;
        border-radius: 50%;
        justify-content: center;
        align-items: center;
      }

      .icon-warn {
        color: #ff9c01;
        background-color: #fff3e1;
      }

      .icon-dander {
        color: #ea3636;
        background-color: #fee;
      }
    }

    .notify-select {
      :deep(.notify-tag-box) {
        display: flex;
        height: 22px;
        padding: 0 6px;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;

        .close-icon {
          font-size: 14px;
          color: #c4c6cc;
        }
      }
    }
  }
</style>
