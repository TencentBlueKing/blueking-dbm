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
    :width="960"
    @closed="handleClose">
    <template #header>
      <div class="header-main">
        {{ titleMap[pageStatus] }}
        【<span class="name">{{ data.name }}</span>
        】
        <BkTag theme="info">
          {{ t('业务') }}
        </BkTag>
      </div>
    </template>
    <div class="monitor-strategy-box">
      <BkForm
        ref="formRef"
        class="edit-form"
        form-type="vertical"
        :model="formModel"
        :rules="formRules">
        <BkFormItem
          :label="t('策略名称')"
          property="strategyName"
          required>
          <BkInput
            v-model="formModel.strategyName"
            :disabled="isEditPage || isReadonlyPage" />
        </BkFormItem>
        <BkFormItem
          :label="t('监控目标')"
          required>
          <MonitorTarget
            ref="monitorTargetRef"
            :bizs-map="bizsMap"
            :cluster-list="clusterList"
            :customs="data.custom_conditions"
            :db-type="dbType"
            :disabled="isReadonlyPage"
            :module-list="moduleList"
            :targets="data.targets" />
        </BkFormItem>
        <BkFormItem
          :label="t('检测规则')"
          required>
          <div class="check-rules">
            <RuleCheck
              v-if="infoRule"
              ref="infoValueRef"
              :data="infoRule"
              :disabled="isReadonlyPage"
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
              :disabled="isReadonlyPage"
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
              :disabled="isReadonlyPage"
              :indicator="data.monitor_indicator"
              :title="t('致命')">
              <DbIcon
                class="title-icon icon-dander"
                type="alert" />
            </RuleCheck>
          </div>
        </BkFormItem>
        <BkFormItem
          :label="t('告警通知')"
          property="notifyRules"
          required>
          <BkCheckboxGroup
            v-model="formModel.notifyRules"
            :disabled="isReadonlyPage">
            <BkCheckbox
              v-for="item in notifyTypes"
              :key="item.label"
              :label="item.value">
              {{ item.label }}
            </BkCheckbox>
          </BkCheckboxGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('告警组')"
          property="notifyTarget"
          required>
          <BkSelect
            v-model="formModel.notifyTarget"
            class="notify-select"
            collapse-tags
            :disabled="isReadonlyPage"
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
        </BkFormItem>
      </BkForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="isReadonlyPage"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkPopConfirm
        :content="t('将会覆盖当前填写的内容，并恢复默认')"
        :disabled="isReadonlyPage"
        placement="top"
        trigger="click"
        width="280"
        @confirm="handleClickConfirmRecoverDefault">
        <BkButton
          class="mr-8"
          :disabled="isReadonlyPage">
          {{ t('恢复默认') }}
        </BkButton>
      </BkPopConfirm>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import {
    clonePolicy,
    updatePolicy,
  } from '@services/monitor';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RuleCheck from '@components/monitor-rule-check/index.vue';

  import { messageSuccess } from '@utils';

  import MonitorTarget from './monitor-target/Index.vue';

  interface Props {
    data: MonitorPolicyModel,
    bizsMap: Record<string, string>,
    dbType: string,
    alarmGroupList: SelectItem<number>[],
    alarmGroupNameMap: Record<string, string>,
    moduleList: SelectItem<string>[],
    clusterList: SelectItem<string>[],
    defaultNotifyId: number,
    pageStatus?: string,
    existedNames?: string[];
  }

  interface Emits {
    (e: 'success'): void,
    (e: 'cancel'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    pageStatus: 'edit',
    existedNames: () => ([]),
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  let rawFormData = '';

  function generateRule(data: MonitorPolicyModel, level: number) {
    const arr = data.test_rules.filter(item => item.level === level);
    return arr.length > 0 ? arr[0] : undefined;
  }

  function initFormData() {
    formModel.strategyName = '';
    formModel.notifyRules = [] as string[];
    formModel.notifyTarget = [] as number[];
    rawFormData = '';
  }

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();

  const monitorTargetRef = ref();
  const infoValueRef = ref();
  const warnValueRef = ref();
  const dangerValueRef = ref();
  const formRef = ref();
  const formModel = reactive({
    strategyName: '',
    notifyRules: [] as string[],
    notifyTarget: [] as number[],
  });

  const isEditPage = computed(() => props.pageStatus === 'edit');
  const isReadonlyPage = computed(() => props.pageStatus === 'read');
  const dangerRule = computed(() => generateRule(props.data, 1));
  const warnRule = computed(() => generateRule(props.data, 2));
  const infoRule = computed(() => generateRule(props.data, 3));

  const titleMap = {
    edit: t('编辑策略'),
    clone: t('克隆策略'),
    read: t('策略'),
  } as Record<string, string>;

  const notifyTypes = [
    {
      value: 'abnormal',
      label: t('告警时触发'),
    },
    {
      value: 'recovered',
      label: t('告警恢复时'),
    },
    {
      value: 'closed',
      label: t('告警关闭时'),
    },
    {
      value: 'ack',
      label: t('告警确认时'),
    },
  ];

  const formRules = {
    strategyName: [
      {
        validator: (value: string) => Boolean(value),
        message: t('策略名称不能为空'),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          if (value.length > 128) {
            return false;
          }
          return true;
        },
        message: t('不能超过n个字符', { n: 128 }),
        trigger: 'blur',
      },
      {
        validator: (value: string) => {
          if (!isEditPage.value) {
            return value !== props.data.name;
          }
          return true;
        },
        message: t('策略名称与原策略名称相同'),
        trigger: 'blur',
      },
      {
        validator: async (value: string) => {
          if (!isEditPage.value) {
            // TODO: 以后看情况是否增加接口支持，暂时先用当前页做冲突检测
            return props.existedNames.every(item => item !== value);
          }
          return true;
        },
        message: t('策略名称重复'),
        trigger: 'blur',
      },
    ],
  };

  const { run: runClonePolicy } = useRequest(clonePolicy, {
    manual: true,
    onSuccess: (cloneResponse) => {
      if (cloneResponse.bkm_id) {
        messageSuccess(t('克隆成功'));
        initFormData();
        emits('success');
        isShow.value = false;
      }
    },
  });

  const { run: runUpdatePolicy } = useRequest(updatePolicy, {
    manual: true,
    onSuccess: (updateResponse) => {
      if (updateResponse.bkm_id) {
        messageSuccess(t('保存成功'));
        initFormData();
        emits('success');
        isShow.value = false;
      }
    },
  });

  watch(formModel, (data) => {
    if (rawFormData === '' && data.notifyRules !== undefined) {
      rawFormData = JSON.stringify(data);
      return;
    }
    if (rawFormData !== '' && rawFormData !== JSON.stringify(data)) {
      window.changeConfirm = true;
    }
  }, {
    deep: true,
  });

  watch(() => props.data, (data) => {
    if (data.id) {
      formModel.strategyName = data.name;
      formModel.notifyRules = _.cloneDeep(data.notify_rules);
      if (isReadonlyPage.value) {
        // 内置策略，展示默认的告警组
        formModel.notifyTarget = [props.defaultNotifyId];
      } else {
        formModel.notifyTarget = data.notify_groups.filter(id => id in props.alarmGroupNameMap);
      }
    }
  });

  const handleDeleteNotifyTargetItem = (id: number) => {
    const index = formModel.notifyTarget.findIndex(item => item === id);
    formModel.notifyTarget.splice(index, 1);
  };

  const handleClickConfirmRecoverDefault = () => {
    formModel.strategyName = props.data.name;
    formModel.notifyRules = _.cloneDeep(props.data.notify_rules);
    formModel.notifyTarget = _.cloneDeep(props.data.notify_groups);
    monitorTargetRef.value.resetValue();
    if (infoValueRef.value) {
      infoValueRef.value.resetValue();
    }
    if (warnValueRef.value) {
      warnValueRef.value.resetValue();
    }
    if (dangerValueRef.value) {
      dangerValueRef.value.resetValue();
    }
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();
    const testRules = [
      infoRule.value ? infoValueRef.value.getValue() : undefined,
      warnRule.value ? warnValueRef.value.getValue() : undefined,
      dangerRule.value ? dangerValueRef.value.getValue() : undefined,
    ];
    const { targets, custom_conditions } = monitorTargetRef.value.getValue();
    const reqParams = {
      targets,
      custom_conditions,
      test_rules: testRules.filter(item => item && item.config.length !== 0),
      notify_rules: formModel.notifyRules,
      notify_groups: formModel.notifyTarget,
    };
    if (!isEditPage.value) {
      // 克隆额外参数
      const params = {
        ...reqParams,
        parent_id: props.data.id, // 父策略id
        name: formModel.strategyName,
        bk_biz_id: currentBizId,
      };
      runClonePolicy(params);
      return;
    }
    runUpdatePolicy(props.data.id, reqParams);
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    initFormData();
    emits('cancel');
    isShow.value = false;
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

  .monitor-strategy-box {
    display: flex;
    width: 100%;
    padding: 24px 40px;
    flex-direction: column;

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
