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
              :disabled="isNameDisabled" />
          </DbFormItem>
          <DbFormItem
            :label="t('是否启用')"
            required>
            <AuthSwitcher
              v-model="formModel.isEnabled"
              v-bk-tooltips="{
                disabled: !enableButtonDisabled,
                content: data.isCustom
                  ? t('父策略为告警兜底，需保持启用以确保告警覆盖')
                  : t('继承自全局策略，启停与全局保持一致'),
              }"
              action-id="global_monitor_policy_start_stop"
              :disabled="enableButtonDisabled"
              :permission="data.permission.global_monitor_policy_start_stop"
              :resource="data.id"
              size="small"
              theme="primary" />
          </DbFormItem>
        </BkCard>
        <BkCard
          class="mt-16"
          is-collapse
          :title="t('监控数据')">
          <PromQL
            v-if="data.isPolicyTypePromQL"
            ref="promqlRef"
            :data="data.agg_info"
            @change="handleDataChange" />
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
              :monitor-policy-id="data.monitor_policy_id"
              @change="handleDataChange" />
          </template>
          <MonitorTarget
            v-if="isMonitorTargetsShow"
            ref="monitorTargetRef"
            :cluster-list="clusterList"
            :customs="data.custom_conditions"
            :is-new="isChildNew"
            :is-promql="props.data.isPolicyTypePromQL"
            :targets="data.targets"
            @change="handleDataChange" />
        </BkCard>
        <TestRules
          ref="testRule"
          class="mt-16"
          :rules="formModel.testRules"
          @change="handleDataChange" />
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
              :data="data.notify_config"
              @change="handleDataChange" />
          </DbFormItem>
        </BkCard>
      </DbForm>
    </div>
    <template #footer>
      <BkPopConfirm
        v-if="popConfirmInfo.content"
        :content="popConfirmInfo.content"
        placement="bottom"
        :title="popConfirmInfo.title"
        trigger="click"
        :width="320"
        @confirm="() => handleConfirm()">
        <BkButton
          :loading="isLoading"
          theme="primary">
          {{ t('确定') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton
        v-else
        :loading="isLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <AuthButton
        v-if="data.isCustom"
        action-id="monitor_policy_edit"
        class="ml-8"
        outline
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

  import { DBTypeInfos, DBTypes, MonitorTargetLevel } from '@common/const';

  import JudgingCondition from '@views/monitor-alarm/common/judging-condition/Index.vue';
  import AggInfo from '@views/monitor-alarm/common/monitor-data/AggInfo.vue';
  import PromQL from '@views/monitor-alarm/common/monitor-data/PromQL.vue';
  import NoticeInterval from '@views/monitor-alarm/common/notice-interval/Index.vue';
  import TestRules from '@views/monitor-alarm/common/test-rules/Index.vue';

  import { messageSuccess } from '@utils';

  import MonitorTarget from './monitor-target/Index.vue';

  interface Props {
    alarmGroupList: SelectItem<string>[];
    alarmGroupNameMap: Record<string, string>;
    appParentInfoMap: Record<number, MonitorPolicyModel>;
    clusterList: SelectItem<string>[];
    data: MonitorPolicyModel;
    dbType: DBTypes;
    existedNames?: string[];
    // 真内置 编辑 -》 clone
    // 真内置 新建子策略 -》 new
    // 假内置 编辑 -》 edit
    // 假内置 新建子策略 -》 new
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
  // const showSwitchEnableTip = ref(false);
  const isNotifyInfoChanged = ref(false);
  const isOtherChanged = ref(false);

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
  const isMonitorTargetsShow = computed(() => props.data.isChild || isChildNew.value);
  const isInnerClone = computed(() => props.data.isInnerReal && props.pageStatus === 'clone');
  const isInnerEdit = computed(() => props.data.isInnerFake && props.pageStatus === 'edit');
  const isCustomEdit = computed(() => props.data.isCustom && props.pageStatus === 'edit');
  const isChildClone = computed(() => props.data.isChild && props.pageStatus === 'clone');
  const isChildNew = computed(() => props.pageStatus === 'new');
  const isNameDisabled = computed(() => isInnerClone.value || isInnerEdit.value || isCustomEdit.value);
  const isEnableChanged = computed(() => props.data.is_enabled !== formModel.isEnabled);

  // 全局启用，启停按钮禁用
  const enableButtonDisabled = computed(() => {
    return (
      (props.data.isInnerReal && props.data.is_enabled) ||
      ((props.data.isInnerFake || props.data.isCustom) && props.appParentInfoMap[props.data.id].is_enabled)
    );
  });

  const titleMap = computed<Record<Props['pageStatus'], string>>(() => ({
    clone: props.data.isChild ? t('克隆子策略') : t('编辑策略'),
    edit: props.data.isChild ? t('编辑子策略') : t('编辑策略'),
    new: t('新建子策略'),
  }));

  const popConfirmInfo = computed(() => {
    if (isInnerClone.value || isInnerEdit.value) {
      // 修改检测参数（当前为继承状态，修改后转为自定义）
      if (!isNotifyInfoChanged.value && isOtherChanged.value) {
        return {
          content: t('修改后将转为自定义管理，不再跟随全局策略更新。'),
          title: t('确认修改该策略？'),
        };
      }

      // 同时修改告警规则并启用策略（当前为继承状态）
      if (isNotifyInfoChanged.value && isEnableChanged.value) {
        return {
          content: t('修改告警规则并启用后，该策略将转为自定义管理，不再跟随全局策略更新。'),
          title: t('确认修改并启用该策略？'),
        };
      }

      // 全局已禁用，启用当前策略（从继承变为自定义）
      if (
        ((props.data.isInnerReal && !props.data.is_enabled) ||
          (props.data.isInnerFake && !props.appParentInfoMap[props.data.id].is_enabled)) &&
        formModel.isEnabled
      ) {
        return {
          content: t('启用后，该策略将转为自定义管理，不再跟随全局策略更新。'),
          title: t('确认启用该策略？'),
        };
      }
    }

    if (isCustomEdit.value) {
      // 全局已禁用，停用当前策略（已是自定义）
      const globalData = props.appParentInfoMap[props.data.id];
      if (!globalData.is_enabled && !formModel.isEnabled) {
        return {
          content: t('停用后，不匹配子策略的对象将失去该告警覆盖。'),
          title: t('确认停用该策略？'),
        };
      }
    }

    return {
      content: '',
      title: '',
    };
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
        message: t('策略名称重复'),
        trigger: 'blur',
        validator: async (value: string) => {
          if (isChildNew.value || isChildClone.value) {
            // TODO: 以后看情况是否增加接口支持，暂时先用当前页做冲突检测
            return props.existedNames.every((item) => item !== value);
          }
          return true;
        },
      },
    ],
  };

  const { loading: cloneLoading, run: runClonePolicy } = useRequest(clonePolicy, {
    manual: true,
    onSuccess: (cloneResponse) => {
      if (cloneResponse.bkm_id) {
        messageSuccess(t('操作成功'));
        emits('success');
        isShow.value = false;
      }
    },
  });

  const { loading: updateLoading, run: runUpdatePolicy } = useRequest(updatePolicy, {
    manual: true,
    onSuccess: (updateResponse) => {
      if (updateResponse.bkm_id) {
        messageSuccess(t('操作成功'));
        emits('success');
        isShow.value = false;
      }
    },
  });

  const { run: runDeletePolicy } = useRequest(deletePolicy, {
    manual: true,
    onSuccess: (isDeleted) => {
      if (isDeleted === null) {
        messageSuccess(t('操作成功'));
      }
    },
  });

  const setChangedInfo = () => {
    setTimeout(() => {
      const { aggInfo, detectsConfig, notifyConfig, testRules } = getConfirmValue();

      isNotifyInfoChanged.value = !_.isEqual(_.pick(props.data, ['notify_config', 'notify_groups', 'notify_rules']), {
        notify_config: notifyConfig,
        notify_groups:
          isInnerClone.value && _.isEqual(formModel.notifyTarget, getBizDefaultGroupIds())
            ? []
            : formModel.notifyTarget, // 真内置编辑默认是内置告警组，此时不判定为修改
        notify_rules: formModel.notifyRules,
      });
      isOtherChanged.value = !_.isEqual(
        _.pick(props.data, ['agg_info', 'detects_config', 'no_data_config', 'test_rules']),
        {
          agg_info: aggInfo,
          detects_config: detectsConfig,
          no_data_config: formModel.noDataConfig,
          test_rules: testRules,
        },
      );
    });
  };

  const setChangedInfoDebounce = _.debounce(setChangedInfo);

  watch(
    formModel,
    () => {
      setChangedInfoDebounce();

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
        formModel.notifyTarget =
          isInnerClone.value || isChildNew.value
            ? getBizDefaultGroupIds()
            : data.notify_groups.filter((id) => id in props.alarmGroupNameMap);
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

  const getStrategyNameWithBizName = () => {
    return `${props.data.name} - ${currentBizInfo?.name}`;
  };

  const getStrategyName = () => {
    // 真内置编辑时，显示为原名称，但提交时需要改为固定格式
    if (isInnerClone.value) {
      return props.data.name;
    }
    // 假内置和自定义策略编辑时，显示为固定格式，但提交时需要改为原名称
    if (isInnerEdit.value || isCustomEdit.value) {
      return props.data.nameDisplay;
    }
    // 新建子策略， 策略名默认为父策略名称 + 数字，依次递增
    if (isChildNew.value) {
      return `${props.data.name} - ${t('子策略')}${props.data.child.length + 1}`;
    }
    // 克隆子策略
    if (isChildClone.value) {
      return `${props.data.name} - ${t('克隆')}`;
    }
    return props.data.name;
  };

  const getBizDefaultGroupIds = () => {
    const groupItem = props.alarmGroupList.find((item) => item.label === `${DBTypeInfos[props.dbType].name}_DBA`);
    return groupItem ? [Number(groupItem.value)] : [];
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

  const handleDataChange = () => {
    setChangedInfoDebounce();
  };

  const getConfirmValue = () => {
    const notifyConfig = noticeIntervalRef.value!.getValue();
    const aggInfo = props.data.isPolicyTypePromQL ? promqlRef.value!.getValue() : aggInfoRef.value!.getValue();
    const detectsConfig = _.cloneDeep(formModel.detectsConfig) as unknown as MonitorPolicyModel['detects_config'];
    detectsConfig.trigger_config.uptime.time_ranges = formModel.detectsConfig.trigger_config.uptime.time_ranges.map(
      (item) => ({
        end: item[1],
        start: item[0],
      }),
    );
    const testRules = testRuleRef.value!.getValue();

    return {
      aggInfo,
      detectsConfig,
      notifyConfig,
      testRules,
    };
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();

    const { aggInfo, detectsConfig, notifyConfig, testRules } = getConfirmValue();
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

    const getParamsName = () => {
      // 真内置编辑时，提交时需要改为固定格式
      if (isInnerClone.value) {
        return getStrategyNameWithBizName();
      }
      // 假内置和自定义策略编辑时，提交时需要改为原名称
      if (isInnerEdit.value || isCustomEdit.value) {
        return props.data.name;
      }
      return formModel.strategyName;
    };

    const getPolicyTag = (): MonitorPolicyModel['policy_tag'] => {
      // 继承时
      if (isInnerClone.value || isInnerEdit.value) {
        // 转为自定义，判断同 popConfirmInfo
        if (
          (!isNotifyInfoChanged.value && isOtherChanged.value) ||
          (isNotifyInfoChanged.value && isEnableChanged.value) ||
          (((props.data.isInnerReal && !props.data.is_enabled) ||
            (props.data.isInnerFake && !props.appParentInfoMap[props.data.id].is_enabled)) &&
            formModel.isEnabled)
        ) {
          return 'custom';
        } else {
          return 'inner';
        }
      }
      // 自定义时
      if (isCustomEdit.value) {
        return 'custom';
      }
      return 'subord';
    };

    const reqParams = {
      agg_info: aggInfo,
      custom_conditions,
      detects_config: detectsConfig,
      is_enabled: formModel.isEnabled,
      name: getParamsName(),
      no_data_config: formModel.noDataConfig,
      notify_config: notifyConfig,
      notify_groups: formModel.notifyTarget,
      notify_rules: formModel.notifyRules,
      policy_tag: getPolicyTag(),
      targets,
      test_rules: testRules,
    };

    if (['clone', 'new'].includes(props.pageStatus)) {
      // 克隆额外参数
      const params = {
        ...reqParams,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
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
