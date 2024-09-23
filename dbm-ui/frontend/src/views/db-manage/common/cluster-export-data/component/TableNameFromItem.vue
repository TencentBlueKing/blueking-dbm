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
  <BkFormItem
    v-bind="$attrs"
    :rules="rules">
    <div ref="rootRef">
      <BkTagInput
        v-model="modelValue"
        allow-auto-match
        allow-create
        class="tippy-element"
        :clearable="false"
        collapse-tags
        has-delete-icon
        :paste-fn="tagInputPasteFn"
        :placeholder="t('请输入DB名称_支持通配符_含通配符的仅支持单个')"
        @click="handleShowTips" />
    </div>
  </BkFormItem>
  <div
    ref="popRef"
    style="font-size: 12px; line-height: 24px; color: #63656e">
    <p>{{ t('匹配任意长度字符串_如a_不允许独立使用') }}</p>
    <p>{{ t('匹配任意单一字符_如a_d') }}</p>
    <p>{{ t('专门指代ALL语义_只能独立使用') }}</p>
    <p>{{ t('注_含通配符的单元格仅支持输入单个对象') }}</p>
    <p>{{ t('Enter完成内容输入') }}</p>
  </div>
</template>

<script setup lang="tsx">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const rootRef = ref();
  const popRef = ref();

  let tippyIns: Instance | undefined;

  const rules = [
    {
      validator: (value: string[]) => !value.some((item) => /\*/.test(item) && item.length > 1),
      message: t('* 只能独立使用'),
      trigger: 'change',
    },
    {
      validator: (value: string[]) => value.every((item) => !/^%$/.test(item)),
      message: t('% 不允许单独使用'),
      trigger: 'change',
    },
    {
      validator: (value: string[]) => {
        if (value.some((item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
      message: t('含通配符的单元格仅支持输入单个对象'),
      trigger: 'change',
    },
  ];

  const tagInputPasteFn = (value: string) => value.split('\n').map((item) => ({ id: item }));

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'top',
      appendTo: () => document.body,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: true,
      offset: [0, 8],
      zIndex: 999999,
      hideOnClick: true,
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
</script>
