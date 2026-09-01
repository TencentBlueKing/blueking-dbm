<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
    10| * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="rootRef"
    class="subscribe-tag-input"
    :class="{ 'is-error': Boolean(errorMessage) }"
    @click="handleShowTips">
    <BkTagInput
      v-model="localValue"
      allow-auto-match
      allow-create
      clearable
      has-delete-icon
      :paste-fn="tagInputPasteFn"
      :placeholder="t('请输入表名，支持通配符')"
      @change="handleTagValueChange" />
    <div
      v-if="errorMessage"
      class="input-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <div style="display: none">
      <div
        ref="popRef"
        style="font-size: 12px; line-height: 24px; color: #63656e">
        <p>{{ t('%：匹配任意长度字符串，如 a%') }}</p>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { type Rules, useValidtor } from '@hooks';

  import { batchSplitRegex } from '@common/regex';

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const { t } = useI18n();

  const rootRef = ref();
  const popRef = ref();
  const localValue = ref<string[]>([]);

  let tippyIns: Instance | undefined;

  const rules: Rules = [
    {
      message: t('不能为空'),
      validator: (value: string[]) => value && value.length > 0,
    },
    {
      message: t('不合法的输入'),
      validator: (value: string[]) => _.some(value, (item) => /^[a-zA-Z0-9_%]+$/.test(item)),
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));

  const handleTagValueChange = (value: string[]) => {
    nextTick(() => {
      validator(value).then(() => {
        window.changeConfirm = true;
      });
    });
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: true,
      content: popRef.value,
      hideOnClick: true,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 18],
      placement: 'top',
      theme: 'light',
      trigger: 'manual',
      zIndex: 9998,
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => {
        if (!localValue.value) {
          return Promise.reject();
        }
        return localValue.value;
      });
    },
  });
</script>
<style lang="less" scoped>
  .subscribe-tag-input {
    position: relative;

    &.is-error {
      :deep(.bk-tag-input-trigger) {
        background: #fff0f1;
      }
    }

    .input-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      z-index: 100;
      display: flex;
      padding-right: 10px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }
</style>
