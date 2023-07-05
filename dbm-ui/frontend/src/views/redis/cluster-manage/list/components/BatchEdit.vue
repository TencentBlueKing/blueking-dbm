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
  <BkPopover
    v-model:is-show="state.isShow"
    :boundary="body"
    class="batch-edit"
    theme="light"
    trigger="manual"
    :width="width">
    <i
      class="db-icon-bulk-edit batch-edit__trigger"
      @click="() => state.isShow = true" />
    <template #content>
      <div class="batch-edit__content">
        <p class="batch-edit__header">
          {{ title || $t('批量编辑') }}
        </p>
        <div class="batch-edit__value">
          <slot :state="state" />
          <p
            v-if="state.isShowError"
            class="batch-edit__value-error">
            {{ state.errorMessage }}
          </p>
        </div>
        <div class="batch-edit__footer">
          <BkButton
            class="mr-8"
            size="small"
            theme="primary"
            @click="handleConfirm">
            {{ $t('确定') }}
          </BkButton>
          <BkButton
            size="small"
            @click="handleCancel">
            {{ $t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  type ErrorInfo = {
    isPass: boolean,
    errorText: string
  }

  const props = defineProps({
    title: {
      type: String,
      default: '',
    },
    width: {
      type: Number,
      default: 540,
    },
    validator: {
      type: Function,
      default: () => (): ErrorInfo => ({ isPass: true, errorText: '' }),
    },
  });

  const emit = defineEmits(['change']);

  const state = reactive({
    isShow: false,
    value: '',
    isShowError: false,
    errorMessage: '',
  });
  const { body } = document;

  async function handleValidate() {
    if (typeof props.validator === 'function') {
      const info: ErrorInfo = await props.validator(state.value);
      state.errorMessage = info.errorText;
      state.isShowError = !info.isPass;
      return info.isPass;
    }

    return true;
  }

  watch(() => state.isShow, (show) => {
    if (show === false) {
      state.value = '';
      state.isShowError = false;
    }
  });

  watch(() => state.value, (value) => {
    value && handleValidate();
  });

  /**
   * confirm batch edit
   */
  async function handleConfirm() {
    await handleValidate();
    if (state.isShowError === true) return;

    emit('change', state.value);
    handleCancel();
  }

  /**
   * close popover
   */
  const handleCancel = () => {
    state.isShow = false;
  };
</script>

<style lang="less" scoped>
  .batch-edit {
    &__trigger {
      margin-left: 5px;
      color: @primary-color;
      cursor: pointer;
    }

    &__content {
      padding: 9px 2px;
    }

    &__header {
      padding-bottom: 16px;
      font-size: @font-size-large;
      color: @title-color;

      span {
        font-size: @font-size-mini;
        color: @default-color;
      }
    }

    &__value {
      position: relative;
      color: @default-color;

      &-error {
        position: absolute;
        bottom: -20px;
        left: 0;
        font-size: @font-size-mini;
        color: @danger-color;
      }
    }

    &__footer {
      margin-top: 16px;
      text-align: right;

      .bk-button {
        min-width: 60px;
        font-size: 12px;
      }
    }
  }
</style>
