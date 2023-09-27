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
        {{ t('编辑策略') }}【{{ data.name }}】
        <BkTag theme="info">
          {{ t('平台配置') }}
        </BkTag>
      </span>
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
              ref="infoValueRef"
              :data="infoRule"
              :indicator="data.monitor_indicator"
              :title="t('提醒')">
              <i class="db-icon-attention-fill title-icon" />
            </RuleCheck>
            <RuleCheck
              ref="warnValueRef"
              :data="warnRule"
              :indicator="data.monitor_indicator"
              :title="t('预警')">
              <i class="db-icon-attention-fill title-icon icon-warn" />
            </RuleCheck>
            <RuleCheck
              ref="dangerValueRef"
              :data="dangerRule"
              :indicator="data.monitor_indicator"
              :title="t('致命')">
              <i class="db-icon-alert title-icon icon-dander" />
            </RuleCheck>
          </div>
        </BkFormItem>
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
        <BkButton class="mr-8">
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

  import { updatePolicy  } from '@services/monitor';

  import { useBeforeClose } from '@hooks';

  import RuleCheck from '@components/monitor-rule-check/index.vue';

  import type { RowData } from '../content/Index.vue';

  interface Props {
    data: RowData,
  }

  interface Emits {
    (e: 'success'): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>();

  function generateRule(data: RowData, level: number) {
    const arr = data.test_rules.filter(item => item.level === level);
    return arr.length > 0 ? arr[0] : undefined;
  }

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const infoValueRef = ref();
  const warnValueRef = ref();
  const dangerValueRef = ref();
  const monitorTarget = ref(t('全部业务'));
  const nofityTarget = ref(t('各业务 DBA'));
  const formRef = ref();
  const formModel = reactive({
    notifyRules: [] as string[],
  });

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
      formModel.notifyRules = _.cloneDeep(data.notify_rules);
    }
  }, {
    immediate: true,
  });

  const handleClickConfirmRecoverDefault = () => {
    formModel.notifyRules = _.cloneDeep(props.data.notify_rules);
    infoValueRef.value.resetValue();
    warnValueRef.value.resetValue();
    dangerValueRef.value.resetValue();
  };

  // 点击确定
  const handleConfirm = async () => {
    await formRef.value.validate();
    const testRules = [
      infoValueRef.value.getValue(),
      warnValueRef.value.getValue(),
      dangerValueRef.value.getValue(),
    ];
    const reqParams = {
      targets: props.data.targets,
      test_rules: testRules.filter(item => item.config.length !== 0),
      notify_rules: formModel.notifyRules,
      notify_groups: props.data.notify_groups,
    };
    const updateResult = await updatePolicy(props.data.id, reqParams);
    if (updateResult.bkm_id) {
      emits('success');
      isShow.value = false;
    }
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    isShow.value = false;
  }

</script>

<style lang="less" scoped>
.edit-strategy-main-box {
  display: flex;
  width: 100%;
  padding: 24px 40px;
  flex-direction: column;

  .item-title {
    margin-bottom: 6px;
    font-weight: normal;
    color: #63656E;
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
