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
      <span>
        {{ pageTitle }}【{{ data.name }}】
        <BkTag theme="info">
          {{ t('业务') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="title-spot item-title">
        {{ t('策略名称') }}<span class="required" />
      </div>
      <BkInput
        v-model="strategyName"
        :disabled="isEditPage"
        @blur="handleSubmitName" />
      <div class="name-tip">
        {{ nameTip }}
      </div>
      <div class="title-spot item-title">
        {{ t('监控目标') }}<span class="required" />
      </div>
      <MonitorTarget
        ref="monitorTargetRef"
        :bizs-map="bizsMap"
        :db-type="dbType"
        :targets="data.targets" />
      <div class="title-spot item-title mt-24">
        {{ t('检测规则') }}<span class="required" />
      </div>
      <div class="check-rules">
        <RuleCheck
          ref="infoValueRef"
          :data="infoRule"
          :title="t('提醒')">
          <i class="db-icon-attention-fill title-icon" />
        </RuleCheck>
        <RuleCheck
          ref="warnValueRef"
          :data="warnRule"
          :title="t('预警')">
          <i class="db-icon-attention-fill title-icon icon-warn" />
        </RuleCheck>
        <RuleCheck
          ref="dangerValueRef"
          :data="dangerRule"
          :title="t('致命')">
          <i class="db-icon-alert title-icon icon-dander" />
        </RuleCheck>
      </div>
      <div class="title-spot item-title mt-24">
        {{ t('告警通知') }}<span class="required" />
      </div>
      <BkCheckboxGroup v-model="notifyRules">
        <BkCheckbox
          v-for="item in notifyTypes"
          :key="item.label"
          :label="item.value">
          {{ item.label }}
        </BkCheckbox>
      </BkCheckboxGroup>
      <div class="title-spot item-title mt-24">
        {{ t('默认通知对象') }}<span class="required" />
      </div>
      <BkSelect
        v-model="nofityTarget"
        class="notify-select"
        collapse-tags
        filterable
        multiple
        multiple-mode="tag">
        <template #tag>
          <div
            v-for="item in nofityTarget"
            :key="item"
            class="notify-tag-box">
            <DbIcon
              style="font-size: 16px"
              type="auth" />
            <span class="dba">{{ alarmGroupNameMap[item] }}</span>
            <DbIcon
              class="close-icon"
              type="close"
              @click="() => handleDeleteNotifyTargetItem(item)" />
          </div>
        </template>
        <BkOption
          v-for="item in alarmGroupList"
          :key="item.value"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
    </div>

    <template #footer>
      <BkButton
        class="mr-8"
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
          class="mr-8">
          {{ t('恢复默认') }}
        </BkButton>
      </BkPopConfirm>

      <BkButton
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { clonePolicy, queryMonitorPolicyList, updatePolicy  } from '@services/monitor';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RuleCheck from '@components/monitor-rule-check/index.vue';

  import type { RowData } from '../type-content/Index.vue';

  import MonitorTarget from './monitor-target/Index.vue';

  interface Props {
    data: RowData,
    bizsMap: Record<string, string>,
    dbType: string,
    alarmGroupList: SelectItem[],
    alarmGroupNameMap: Record<string, string>,
    pageStatus?: string,
  }

  interface Emits {
    (e: 'success'): void
  }

  const props = withDefaults(defineProps<Props>(), {
    pageStatus: 'edit',
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();
  const { currentBizId } = useGlobalBizs();

  const monitorTargetRef = ref();
  const notifyRules = ref<string[]>([]);
  const nofityTarget = ref<number[]>([]);
  const infoValueRef = ref();
  const warnValueRef = ref();
  const dangerValueRef = ref();
  const strategyName = ref('');
  const nameTip = ref('');

  const isEditPage = computed(() => props.pageStatus === 'edit');
  const pageTitle = computed(() => (isEditPage.value ? t('编辑策略') : t('克隆策略')));
  const dangerRule = computed(() => generateRule(props.data, 1));
  const warnRule = computed(() => generateRule(props.data, 2));
  const infoRule = computed(() => generateRule(props.data, 3));

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

  watch(() => props.data, (data) => {
    if (data) {
      strategyName.value = data.name;
      notifyRules.value = _.cloneDeep(data.notify_rules);
      nofityTarget.value = _.cloneDeep(data.notify_groups);
    }
  }, {
    immediate: true,
  });

  const checkName = async () => {
    // 克隆才需要校验
    if (strategyName.value === props.data.name) {
      nameTip.value = t('策略名称与原策略名称相同');
      return false;
    }
    const ret = await queryMonitorPolicyList({
      bk_biz_id: currentBizId,
      db_type: props.dbType,
      name: strategyName.value,
      limit: 10,
      offset: 0,
    });
    if (ret.results.length !== 0) {
      nameTip.value = t('策略名称重复');
      return false;
    }
    nameTip.value = '';
    return true;
  };

  const handleSubmitName = () => {
    if (!isEditPage.value) {
      checkName();
    }
  };

  const handleDeleteNotifyTargetItem = (id: number) => {
    const index = nofityTarget.value.findIndex(item => item === id);
    nofityTarget.value.splice(index, 1);
  };

  const handleClickConfirmRecoverDefault = () => {
    strategyName.value = props.data.name;
    notifyRules.value = _.cloneDeep(props.data.notify_rules);
    nofityTarget.value = _.cloneDeep(props.data.notify_groups);
    monitorTargetRef.value.resetValue();
    infoValueRef.value.resetValue();
    warnValueRef.value.resetValue();
    dangerValueRef.value.resetValue();
  };

  // 点击确定
  const handleConfirm = async () => {
    if (!isEditPage.value) {
      const status = await checkName();
      if (!status) {
        return;
      }
    }
    const testRules = [
      infoValueRef.value.getValue(),
      warnValueRef.value.getValue(),
      dangerValueRef.value.getValue(),
    ];
    const reqParams = {
      targets: monitorTargetRef.value.getValue().map((item: { id: string; value: string[]; }) => ({
        rule: {
          key: item.id,
          value: item.value,
        },
        level: item.id,
      })),
      test_rules: testRules.filter(item => item.config.length !== 0),
      notify_rules: notifyRules.value,
      notify_groups: nofityTarget.value,
    };
    if (!isEditPage.value) {
      // 克隆额外参数
      const params = {
        ...reqParams,
        parent_id: props.data.id, // 父策略id
        name: strategyName.value,
        bk_biz_id: currentBizId,
      };
      console.log('params: ', params);
      const r = await clonePolicy(params);
      console.log('clone policy: ', r);
      emits('success');
      isShow.value = false;
      return;
    }
    console.log('params: ', reqParams);
    const r = await updatePolicy(props.data.id, reqParams);
    console.log('edit policy: ', r);
    emits('success');
    isShow.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    isShow.value = false;
  }

  function generateRule(data: RowData, level: number) {
    const arr = data.test_rules.filter(item => item.level === level);
    return arr.length > 0 ? arr[0] : {
      config: [],
      level,
      type: 'Threshold',
      unit_prefix: data.test_rules[0].unit_prefix,
    };
  }

</script>

<style lang="less" scoped>
.main-box {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .item-title {
    margin-bottom: 6px;
    font-weight: normal;
    color: #63656E;
  }

  .name-tip {
    height: 20px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #EA3636;
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
      color: #3A84FF;
      background-color: #F0F5FF;
      border: none;
      border-radius: 50%;
      justify-content: center;
      align-items: center;
    }

    .icon-warn {
      color: #FF9C01;
      background-color: #FFF3E1;
    }

    .icon-dander {
      color: #EA3636;
      background-color: #FEE;
    }
  }

  .notify-select {
    :deep(.bk-select-tag-wrapper) {
      // padding: 4px;
      gap: 4px
    }

    :deep(.notify-tag-box) {
      display: flex;
      height: 22px;
      padding: 0 6px;
      background: #F0F1F5;
      border-radius: 2px;
      align-items: center;

      .close-icon {
        font-size: 14px;
        color: #C4C6CC;
      }
    }
  }
}


</style>
