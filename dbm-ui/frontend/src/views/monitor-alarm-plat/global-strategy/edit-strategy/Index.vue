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
        {{ t('编辑策略') }}【{{ data.strategyName }}】
        <BkTag theme="info">
          {{ t('平台配置') }}
        </BkTag>
      </span>
    </template>
    <div class="main-box">
      <div class="title-spot item-title">
        {{ t('策略名称') }}<span class="required" />
      </div>
      <BkInput
        disabled
        size="default"
        :value="data.strategyName" />
      <div class="title-spot item-title mt-24">
        {{ t('监控目标') }}<span class="required" />
      </div>
      <BkSelect
        v-model="monitorTarget"
        disabled>
        <BkOption>{{ data.target }}</BkOption>
      </BkSelect>
      <div class="title-spot item-title mt-24">
        {{ t('检测规则') }}<span class="required" />
      </div>
      <div class="check-rules">
        <RuleCheck
          ref="infoValueRef"
          :title="t('提醒')">
          <i class="db-icon-attention-fill title-icon" />
        </RuleCheck>
        <RuleCheck
          ref="warnValueRef"
          :title="t('预警')">
          <i class="db-icon-attention-fill title-icon icon-warn" />
        </RuleCheck>
        <RuleCheck
          ref="dangerValueRef"
          :title="t('致命')">
          <i class="db-icon-alert title-icon icon-dander" />
        </RuleCheck>
      </div>
      <div class="title-spot item-title mt-24">
        {{ t('告警通知') }}<span class="required" />
      </div>
      <BkCheckboxGroup v-model="notifyValue">
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
        disabled
        multiple-mode="tag">
        <BkOption>{{ data.notifyTarget }}</BkOption>
        <template #tag>
          <div class="notify-tag-box">
            <DbIcon
              style="font-size: 16px"
              type="auth" />
            <span class="dba">{{ data.notifyTarget }}</span>
            <DbIcon
              class="close-icon"
              type="close" />
          </div>
        </template>
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
        content="将会覆盖当前填写的内容，并恢复默认"
        placement="top"
        trigger="click"
        width="280"
        @confirm="{handleClickConfirmRecoverDefault}">
        <BkButton
          class="mr-8"
          @click="handleClickRecoverDefault">
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
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useBeforeClose } from '@hooks';

  import type { RowData } from '../type-content/Index.vue';

  import RuleCheck from './rule-check/Index.vue';

  interface Props {
    data: RowData,
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>();

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const notifyValue = ref([]);
  const infoValueRef = ref();
  const warnValueRef = ref();
  const dangerValueRef = ref();

  const monitorTarget = computed(() => props.data.target);
  const nofityTarget = computed(() => props.data.notifyTarget);

  const notifyTypes = [
    {
      value: '0',
      label: t('告警时触发'),
    },
    {
      value: '1',
      label: t('告警恢复时'),
    },
    {
      value: '2',
      label: t('告警关闭时'),
    },
    {
      value: '3',
      label: t('告警确认时'),
    },
  ];

  const handleClickRecoverDefault = () => {
    console.log('handleClickRecoverDefault');
  };
  const handleClickConfirmRecoverDefault = () => {
    console.log('handleClickConfirmRecoverDefault');
  };

  // 点击确定
  const handleConfirm = () => {
    const param = {
      notify_arr: infoValueRef.value.getValue(),
      warn_arr: warnValueRef.value.getValue(),
      danger_arr: dangerValueRef.value.getValue(),
      notifys: notifyValue.value,
    };
    console.log('params: ', param);
    // isShow.value = false;
  };

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    isShow.value = false;
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
