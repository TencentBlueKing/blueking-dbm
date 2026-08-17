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
  <DbSideslider
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
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formModel">
        <BkCard
          is-collapse
          :title="t('基本信息')">
          <BkFormItem
            :label="t('策略名称')"
            required>
            <BkInput
              disabled
              :value="data.name" />
          </BkFormItem>
          <BkFormItem
            :label="t('是否启用')"
            required>
            <BkSwitcher
              v-model="formModel.isEnabled"
              size="small"
              theme="primary" />
          </BkFormItem>
        </BkCard>
        <BkCard
          class="mt-16"
          is-collapse
          :title="t('监控数据')">
          <PromQL
            v-if="data.isPolicyTypePromQL"
            ref="promqlRef"
            :data="data.agg_info" />
          <template v-else>
            <BkAlert
              :title="
                t(
                  '指标由平台预置，不可增删或修改指标名。单指标策略允许修改汇聚方法和汇聚周期；多指标策略仅允许修改汇聚周期。',
                )
              " />
            <AggInfo
              ref="aggInfo"
              class="mt-16"
              :data="data.agg_info"
              :expression="data.expression"
              :is-multiple="data.isPolicyTypeMulti"
              :monitor-policy-id="data.monitor_policy_id" />
          </template>
        </BkCard>
        <TestRules
          ref="testRule"
          class="mt-16"
          :rules="formModel.testRules" />
        <JudgingCondition
          v-model="formModel"
          class="mt-16"
          :monitor-policy-id="data.monitor_policy_id" />
        <BkCard
          class="mt-16"
          is-collapse
          :title="t('通知设置')">
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
          <BkFormItem
            :label="t('通知间隔')"
            required>
            <NoticeInterval
              ref="noticeInterval"
              :data="data.notify_config" />
          </BkFormItem>
        </BkCard>
      </DbForm>
    </div>
    <template #footer>
      <BkPopConfirm
        :content="t('修改后将自动同步至所有业务（已自定义的业务策略不受影响）。')"
        placement="bottom"
        :title="t('确认修改该策略？')"
        trigger="click"
        :width="320"
        @confirm="() => handleConfirm()">
        <AuthButton
          action-id="global_alarm_policy_manage"
          :disabled="resetLoading"
          :loading="updateLoading"
          :permission="data.permission.global_alarm_policy_manage"
          :resource="dbType"
          theme="primary">
          {{ t('确定') }}
        </AuthButton>
      </BkPopConfirm>
      <AuthButton
        action-id="global_alarm_policy_manage"
        class="ml-8"
        :disabled="updateLoading"
        :loading="resetLoading"
        outline
        :permission="data.permission.global_alarm_policy_manage"
        :resource="dbType"
        theme="primary"
        @click="() => handleResetClickConfirm()">
        {{ t('恢复初始值') }}
      </AuthButton>
      <BkButton
        class="ml-8"
        :disabled="updateLoading || resetLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { type UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { resetGlobalStrategy, updatePolicy } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import { DBTypes } from '@common/const';

  import JudgingCondition from '@views/monitor-alarm/common/judging-condition/Index.vue';
  import AggInfo from '@views/monitor-alarm/common/monitor-data/AggInfo.vue';
  import PromQL from '@views/monitor-alarm/common/monitor-data/PromQL.vue';
  import NoticeInterval from '@views/monitor-alarm/common/notice-interval/Index.vue';
  import TestRules from '@views/monitor-alarm/common/test-rules/Index.vue';
  import { getDbaLabel } from '@views/monitor-alarm/common/utils';

  import { messageSuccess } from '@utils';

  interface Props {
    data: MonitorPolicyModel;
    dbType: DBTypes;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const aggInfoRef = useTemplateRef('aggInfo');
  const promqlRef = useTemplateRef('promqlRef');
  const testRuleRef = useTemplateRef('testRule');
  const noticeIntervalRef = useTemplateRef('noticeInterval');

  // const monitorTarget = ref(t('全部业务'));
  const formRef = ref();
  const nofityTarget = ref(`{${getDbaLabel(props.dbType)}}`);
  // const showSwitchEnableTip = ref(false);

  const formModel = reactive({
    detectsConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['detectsConfig'],
    isEnabled: false,
    noDataConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['noDataConfig'],
    notifyRules: [] as string[],
    testRules: [] as ComponentProps<typeof TestRules>['rules'],
  });

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

  const { loading: resetLoading, run: runResetGlobalStrategy } = useRequest(resetGlobalStrategy, {
    manual: true,
    onSuccess: () => {
      emits('success');
      isShow.value = false;
      messageSuccess(t('恢复初始值成功'));
    },
  });

  watch(
    () => props.data,
    (data) => {
      if (data.id) {
        formModel.isEnabled = data.is_enabled;
        formModel.testRules = _.cloneDeep(data.test_rules);
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

  // const handleSwitchEnableClickConfirm = () => {
  //   formModel.isEnabled = false;
  //   showSwitchEnableTip.value = false;
  // };

  // const handleSwitchEnableCancelConfirm = () => {
  //   showSwitchEnableTip.value = false;
  // };

  // const handleChangeSwitch = () => {
  //   if (!formModel.isEnabled) {
  //     showSwitchEnableTip.value = true;
  //     formModel.isEnabled = !formModel.isEnabled;
  //   }
  // };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();

    const aggInfo = props.data.isPolicyTypePromQL ? promqlRef.value!.getValue() : aggInfoRef.value!.getValue();
    const testRules = testRuleRef.value!.getValue();
    const notifyConfig = noticeIntervalRef.value!.getValue();
    const detectsConfig = _.cloneDeep(formModel.detectsConfig) as unknown as MonitorPolicyModel['detects_config'];
    detectsConfig.trigger_config.uptime.time_ranges = formModel.detectsConfig.trigger_config.uptime.time_ranges.map(
      (item) => ({
        end: item[1],
        start: item[0],
      }),
    );

    const reqParams = {
      agg_info: aggInfo,
      custom_conditions: props.data.custom_conditions,
      detects_config: detectsConfig,
      is_enabled: formModel.isEnabled,
      no_data_config: formModel.noDataConfig,
      notify_config: {
        ...props.data.notify_config,
        ...notifyConfig,
      },
      notify_groups: props.data.notify_groups,
      notify_rules: formModel.notifyRules,
      policy_tag: 'inner' as const,
      targets: props.data.targets,
      test_rules: testRules.filter((item) => item && item.config.length !== 0),
    };
    runUpdatePolicy(props.data.id, reqParams);
  };

  const handleResetClickConfirm = () => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定恢复'),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        runResetGlobalStrategy({ policy_id: props.data.id });
      },
      subTitle: (
        <div style='padding: 12px 16px; background: #F5F7FA; color: #4D4F56'>
          {t('恢复后将还原为平台预设的初始配置，并自动同步至所有业务（已自定义的业务策略不受影响）。')}
        </div>
      ),
      title: t('确认恢复初始值？'),
    });
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

    :deep(.bk-card-body) {
      padding: 16px 24px;
    }

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
