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
    :width="540">
    <i
      class="db-icon-bulk-edit batch-edit__trigger"
      @click="() => state.isShow = true" />
    <template #content>
      <div class="batch-edit__content">
        <p class="batch-edit__header">
          {{ $t('快捷编辑') }}
          <span>{{ $t('通过换行分隔_快速批量编辑多个域名') }}</span>
        </p>
        <div
          class="batch-edit__domain"
          :style="{ '--offset': `${state.offsetWidth}px` }">
          <p class="batch-edit__domain-name">
            <span ref="moduleNameRef">{{ moduleName }}db.</span>
            <span class="batch-edit__domain-underline" />.{{ appName }}.db
          </p>
          <BkInput
            v-model="state.value"
            class="batch-edit__domain-input"
            :placeholder="$t('以小写英文字母开头_且只能包含小写英文字母_数字_连字符_多个换行分隔')"
            :rows="textareaRows"
            type="textarea" />
          <p
            v-if="validateState.isShow"
            class="batch-edit__domain-error">
            {{ validateState.errorTxt }}
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { nameRegx } from '@common/regex';

  interface Props {
    moduleName?: string,
    appName?: string,
  }

  interface Emits {
    (e: 'change', value: string[]): void
  }

  withDefaults(defineProps<Props>(), {
    moduleName: '',
    appName: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const errorTxt = {
    rule: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
    repeat: t('输入域名重复'),
  };

  const state = reactive({
    isShow: false,
    value: '',
    offsetWidth: 0,
  });
  const validateState = reactive({
    isShow: false,
    errorTxt: '',
  });
  const { body } = document;
  const textareaRows = computed(() => {
    const rows = state.value.split('\n').length;
    if (rows <= 5) {
      return 5;
    }
    return rows > 10 ? 10 : rows;
  });

  /**
   * 获取输入框 arrow 偏移量
   */
  const moduleNameRef = ref<HTMLSpanElement>();
  watch(() => state.isShow, (show) => {
    nextTick(() => {
      if (moduleNameRef.value) {
        state.offsetWidth = moduleNameRef.value.offsetWidth + 22;
      }
    });
    if (show === false) {
      state.value = '';
      validateState.isShow = false;
    }
  });

  /**
   * validate batch edit value
   */
  const handleValidate = () => {
    const newDomains = state.value.split('\n');
    const validate = newDomains.every(key => nameRegx.test(key));
    if (!validate) {
      validateState.errorTxt = errorTxt.rule;
      validateState.isShow = !validate;
      return validate;
    }
    // 校验名称是否重复
    const uniqDomains = _.uniq(newDomains);
    const hasRepeat = newDomains.length !== uniqDomains.length;
    validateState.errorTxt = errorTxt.repeat;
    validateState.isShow = hasRepeat;
    return !hasRepeat;
  };

  watch(() => state.value, (value) => {
    value && handleValidate();
  });

  /**
   * confirm batch edit
   */
  const handleConfirm = () => {
    handleValidate();
    if (validateState.isShow === true) return;

    const newDomains = state.value.split('\n');
    emits('change', newDomains);
    handleCancel();
  };

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

  &__domain {
    position: relative;
    color: @default-color;

    &-name {
      word-wrap: break-word;
    }

    &-underline {
      position: relative;
      display: inline-block;
      width: 54px;
      height: 1px;
      margin: 0 2px;
      color: @default-color;
      background-color: #c4c6cc;

      &::after {
        position: absolute;
        top: -4px;
        left: 50%;
        z-index: 1;
        width: 6px;
        height: 6px;
        background-color: white;
        border: 1px solid transparent;
        border-bottom-color: #c4c6cc;
        border-left-color: #c4c6cc;
        content: '';
        transform: translateX(-50%) rotate(-45deg);
      }
    }

    &-input {
      position: relative;
      margin: 12px 0 16px;

      &::before {
        position: absolute;
        top: -4px;
        left: var(--offset);
        width: 6px;
        height: 6px;
        background-color: @white-color;
        border: 1px solid transparent;
        border-top-color: @border-light-gray;
        border-left-color: @border-light-gray;
        content: "";
        transform: rotateZ(45deg);
      }

      &.is-focused {
        &::before {
          border-top-color: @border-primary;
          border-left-color: @border-primary;
        }
      }
    }

    &-error {
      position: absolute;
      bottom: -4px;
      left: 0;
      font-size: @font-size-mini;
      color: @danger-color;
    }
  }

  &__footer {
    text-align: right;

    .bk-button {
      min-width: 60px;
      font-size: 12px;
    }
  }
}
</style>
