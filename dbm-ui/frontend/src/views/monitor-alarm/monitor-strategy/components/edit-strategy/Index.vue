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
    :is-show="isShow"
    :width="1110"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        {{ titleMap[pageStatus] }}
        【
        <span class="name">{{ data.nameDisplay }}</span>
        】
        <BkTag theme="info">
          {{ t('业务') }}
        </BkTag>
      </div>
    </template>
    <div class="monitor-strategy-box">
      <DbForm
        ref="formRef"
        class="edit-form"
        form-type="vertical"
        :model="formModel"
        :rules="formRules">
        <BkCard
          is-collapse
          :title="t('基本信息')">
          <DbFormItem
            :label="t('策略名称')"
            property="strategyName"
            required>
            <BkInput
              v-model="formModel.strategyName"
              :disabled="pageStatus === 'edit'" />
          </DbFormItem>
          <DbFormItem
            :label="t('是否启用')"
            required>
            <BkPopConfirm
              :content="t('停用后，所有的业务将会停用该策略，请谨慎操作！')"
              :is-show="showSwitchEnableTip"
              placement="bottom"
              :popover-options="{
                disabled: data.isInner || !formModel.isEnabled,
              }"
              :title="t('确认停用该策略？')"
              trigger="click"
              width="320"
              @cancel="() => handleSwitchEnableCancelConfirm()"
              @confirm="() => handleSwitchEnableClickConfirm()">
              <AuthSwitcher
                v-model="formModel.isEnabled"
                action-id="global_monitor_policy_start_stop"
                :disabled="data.isInner"
                :permission="data.permission.global_monitor_policy_start_stop"
                :resource="data.id"
                size="small"
                theme="primary"
                @change="() => handleChangeSwitch()" />
            </BkPopConfirm>
          </DbFormItem>
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
          <MonitorTarget
            v-if="isMonitorTargetsShow"
            ref="monitorTargetRef"
            :cluster-list="clusterList"
            :customs="data.custom_conditions"
            :is-new="props.pageStatus === 'new'"
            :is-promql="props.data.isPolicyTypePromQL"
            :targets="data.targets" />
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
          <DbFormItem
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
          </DbFormItem>
          <DbFormItem
            :label="t('告警组')"
            property="notifyTarget"
            required>
            <BkSelect
              v-model="formModel.notifyTarget"
              class="notify-select"
              collapse-tags
              filterable
              multiple
              multiple-mode="tag">
              <template #tag="{ selected }">
                <BkTag
                  v-for="item in selected"
                  :key="item"
                  closable
                  @close="() => handleDeleteNotifyTargetItem(item.value)">
                  <template #icon>
                    <DbIcon
                      class="alarm-icon"
                      type="yonghuzu" />
                  </template>
                  {{ alarmGroupNameMap[item.value] }}
                </BkTag>
              </template>
              <BkOption
                v-for="item in alarmGroupList"
                :key="item.value"
                :label="item.label"
                :value="item.value" />
            </BkSelect>
          </DbFormItem>
          <DbFormItem
            :label="t('通知间隔')"
            required>
            <NoticeInterval
              ref="noticeInterval"
              :data="data.notify_config" />
          </DbFormItem>
        </BkCard>
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        :loading="isLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <AuthButton
        v-if="data.isCustom"
        action-id="monitor_policy_edit"
        class="ml-8"
        :permission="data.permission.monitor_policy_edit"
        :resource="data.id"
        theme="primary"
        @click="() => handleResetToDefault()">
        {{ t('恢复默认') }}
      </AuthButton>
      <BkButton
        class="ml-8"
        :disabled="isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { computed, type UnwrapRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { clonePolicy, deletePolicy, updatePolicy } from '@services/source/monitor';

  import { useGlobalBizs } from '@stores';

  import { MonitorTargetLevel } from '@common/const';

  import JudgingCondition from '@views/monitor-alarm/common/judging-condition/Index.vue';
  import AggInfo from '@views/monitor-alarm/common/monitor-data/AggInfo.vue';
  import PromQL from '@views/monitor-alarm/common/monitor-data/PromQL.vue';
  import NoticeInterval from '@views/monitor-alarm/common/notice-interval/Index.vue';
  import TestRules from '@views/monitor-alarm/common/test-rules/Index.vue';

  import { messageSuccess } from '@utils';

  import MonitorTarget from './monitor-target-new/Index.vue';

  interface Props {
    alarmGroupList: SelectItem<string>[];
    alarmGroupNameMap: Record<string, string>;
    clusterList: SelectItem<string>[];
    data: MonitorPolicyModel;
    existedNames?: string[];
    // 内置 编辑 -》 clone
    // 内置 新建子策略 -》 new
    // 自定义 编辑 -》 edit
    // 自定义 新建子策略 -》 new
    // 子策略 编辑 -》 edit
    // 子策略 克隆 -》 clone
    pageStatus: 'edit' | 'clone' | 'new';
  }

  interface Emits {
    (e: 'success'): void;
    (e: 'cancel'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    existedNames: () => [],
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  let rawFormData = '';

  const { t } = useI18n();
  const { currentBizId, currentBizInfo } = useGlobalBizs();

  const aggInfoRef = useTemplateRef('aggInfo');
  const promqlRef = useTemplateRef('promqlRef');
  const testRuleRef = useTemplateRef('testRule');
  const noticeIntervalRef = useTemplateRef('noticeInterval');

  const formRef = ref();
  const monitorTargetRef = ref();
  // const innerNotifyTarget = ref([props.dbType]);
  const showSwitchEnableTip = ref(false);

  const formModel = reactive({
    detectsConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['detectsConfig'],
    isEnabled: false,
    noDataConfig: {} as ComponentProps<typeof JudgingCondition>['modelValue']['noDataConfig'],
    notifyRules: [] as string[],
    notifyTarget: [] as number[],
    strategyName: '',
    testRules: [] as ComponentProps<typeof TestRules>['rules'],
  });

  const isLoading = computed(() => updateLoading.value || cloneLoading.value);
  const isCloneStratgy = computed(() => ['clone', 'new'].includes(props.pageStatus));
  const isMonitorTargetsShow = computed(() => props.data.isChild || props.pageStatus === 'new');

  const titleMap = computed<Record<Props['pageStatus'], string>>(() => ({
    clone: props.data.isChild ? t('克隆策略') : t('编辑策略'),
    edit: t('编辑策略'),
    new: t('新建子策略'),
  }));

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

  const formRules = {
    strategyName: [
      {
        message: t('策略名称不能为空'),
        trigger: 'blur',
        validator: (value: string) => Boolean(value),
      },
      {
        message: t('不能超过n个字符', { n: 128 }),
        trigger: 'blur',
        validator: (value: string) => {
          if (value.length > 128) {
            return false;
          }
          return true;
        },
      },
      {
        message: t('策略名称与原策略名称相同'),
        trigger: 'blur',
        validator: (value: string) => {
          if (props.pageStatus === 'edit') {
            return true;
          }
          return value !== props.data.name;
        },
      },
      {
        message: t('策略名称重复'),
        trigger: 'blur',
        validator: async (value: string) => {
          if (props.pageStatus === 'edit') {
            return true;
          }
          // TODO: 以后看情况是否增加接口支持，暂时先用当前页做冲突检测
          return props.existedNames.every((item) => item !== value);
        },
      },
    ],
  };

  const { loading: cloneLoading, run: runClonePolicy } = useRequest(clonePolicy, {
    manual: true,
    onSuccess: (cloneResponse) => {
      if (cloneResponse.bkm_id) {
        messageSuccess(t('克隆成功'));
        emits('success');
        isShow.value = false;
      }
    },
  });

  const { loading: updateLoading, run: runUpdatePolicy } = useRequest(updatePolicy, {
    manual: true,
    onSuccess: (updateResponse) => {
      if (updateResponse.bkm_id) {
        messageSuccess(t('保存成功'));
        emits('success');
        isShow.value = false;
      }
    },
  });

  const { run: runDeletePolicy } = useRequest(deletePolicy, {
    manual: true,
    onSuccess: (isDeleted) => {
      if (isDeleted === null) {
        messageSuccess(t('删除成功'));
      }
    },
  });

  watch(
    formModel,
    () => {
      if (rawFormData === '' && formModel.notifyRules !== undefined) {
        rawFormData = JSON.stringify(formModel);
        return;
      }
      if (rawFormData !== '' && rawFormData !== JSON.stringify(formModel)) {
        window.changeConfirm = true;
      }
    },
    {
      deep: true,
    },
  );

  watch(
    () => props.data,
    (data) => {
      if (data.id) {
        formModel.isEnabled = data.is_enabled;
        formModel.testRules = _.cloneDeep(data.test_rules);
        formModel.strategyName = getStrategyName();
        formModel.notifyRules = _.cloneDeep(data.notify_rules);
        formModel.notifyTarget = data.notify_groups.filter((id) => id in props.alarmGroupNameMap);
        formModel.noDataConfig = _.cloneDeep(data.no_data_config);

        const detectsConfig = _.cloneDeep(data.detects_config) as unknown as UnwrapRef<
          typeof formModel
        >['detectsConfig'];
        detectsConfig.trigger_config.uptime.time_ranges = _.cloneDeep(
          data.detects_config.trigger_config.uptime.time_ranges,
        ).map((item) => [item.start, item.end] as [string, string]);
        formModel.detectsConfig = detectsConfig;
      }
    },
  );

  const handleDeleteNotifyTargetItem = (id: number) => {
    const index = formModel.notifyTarget.findIndex((item) => item === id);
    formModel.notifyTarget.splice(index, 1);
  };

  const getStrategyName = () =>
    isCloneStratgy.value ? `${props.data.name} - ${currentBizInfo?.name}` : props.data.name;

  const handleSwitchEnableClickConfirm = () => {
    formModel.isEnabled = false;
    showSwitchEnableTip.value = false;
  };

  const handleSwitchEnableCancelConfirm = () => {
    showSwitchEnableTip.value = false;
  };

  const handleChangeSwitch = () => {
    if (!formModel.isEnabled) {
      showSwitchEnableTip.value = true;
      formModel.isEnabled = !formModel.isEnabled;
    }
  };

  const handleResetToDefault = () => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定恢复'),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        runDeletePolicy({ id: props.data.id });
      },
      subTitle: (
        <>
          <div class='mb-16'>
            {t('策略名称：')}
            {props.data.name}
          </div>
          <div style='padding: 12px 16px; background: #F5F7FA; color: #4D4F56'>
            {t('恢复默认将覆盖当前所有自定义修改，恢复为全局策略配置。此操作不可撤销。')}
          </div>
        </>
      ),
      title: t('确认恢复为默认？'),
    });
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();

    const aggInfo = props.data.isPolicyTypePromQL ? promqlRef.value!.getValue() : aggInfoRef.value!.getValue();
    const testRules = testRuleRef.value!.getValue();
    const notifyConfig = noticeIntervalRef.value!.getValue();
    const { custom_conditions, targets } = isMonitorTargetsShow.value
      ? monitorTargetRef.value.getValue()
      : {
          custom_conditions: [],
          targets: [
            {
              level: MonitorTargetLevel.BIZ,
              rule: {
                key: MonitorTargetLevel.BIZ,
                method: props.data.isPolicyTypePromQL ? '=' : 'eq',
                value: [currentBizId],
              },
            },
          ],
        };
    const detectsConfig = _.cloneDeep(formModel.detectsConfig) as unknown as MonitorPolicyModel['detects_config'];
    detectsConfig.trigger_config.uptime.time_ranges = formModel.detectsConfig.trigger_config.uptime.time_ranges.map(
      (item) => ({
        end: item[1],
        start: item[0],
      }),
    );

    const reqParams = {
      agg_info: aggInfo,
      custom_conditions,
      detects_config: detectsConfig,
      is_enabled: formModel.isEnabled,
      no_data_config: formModel.noDataConfig,
      notify_config: notifyConfig,
      notify_groups: formModel.notifyTarget,
      notify_rules: formModel.notifyRules,
      targets,
      test_rules: testRules.filter((item) => item && item.config.length !== 0),
    };

    if (isCloneStratgy.value) {
      // 克隆额外参数
      const params = {
        ...reqParams,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        name: formModel.strategyName,
        // parent_id优先取克隆策略的parent_id，如果parent_id为空证明该策略是一条平台策略，就取策略id
        parent_id: props.data.parent_id ? props.data.parent_id : props.data.id,
      };
      runClonePolicy(params);
      return;
    }
    runUpdatePolicy(props.data.id, reqParams);
  };

  const handleClose = () => {
    emits('cancel');
    isShow.value = false;
  };
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

  .monitor-strategy-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

    :deep(.bk-card-body) {
      padding: 16px 24px;
    }

    .edit-form {
      :deep(.bk-form-label) {
        font-weight: 700;
      }
    }

    .item-title {
      margin-bottom: 6px;
      font-weight: normal;
      color: #63656e;
    }

    .name-tip {
      height: 20px;
      margin-bottom: 6px;
      font-size: 12px;
      color: #ea3636;
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
      :deep(.alarm-icon) {
        font-size: 18px;
        color: #979ba5;
      }

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
