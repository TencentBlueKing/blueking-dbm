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
  <BkForm
    ref="dbFormRef"
    :model="model"
    v-bind="$attrs"
    @click="handleUserChange">
    <slot />
  </BkForm>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';

  const props = defineProps({
    model: {
      type: Object,
      default: () => ({}),
    },
    autoLabelWidth: {
      type: Boolean,
      default: false,
    },
  });

  const dbFormRef = ref();

  watch(() => props.model, () => {
    if (isUserChange.value) {
      window.changeConfirm = true;
    }
  }, { deep: true });

  /** 用户主动操作变更表单 */
  const isUserChange = ref(false);
  const handleUserChange = () => isUserChange.value = true;

  const getCssStyle = (el: HTMLElement, prop: string) => window.getComputedStyle(el, null).getPropertyValue(prop);
  const calcLableWidth = () => {
    const formWrapper = dbFormRef.value?.$el as HTMLFormElement;
    if (formWrapper) {
      const labels: HTMLDivElement[] = Array.from(formWrapper.querySelectorAll('.bk-form-label'));
      const div = document.createElement('div');
      div.style.position = 'fixed';
      div.style.zIndex = '-99999';
      div.style.visibility = 'hidden';
      div.style.whiteSpace = 'nowrap';
      document.body.appendChild(div);

      let maxWidth = 150;
      for (const label of labels) {
        div.style.fontSize = getCssStyle(label, 'font-size') || '14px';
        div.style.fontWeight = getCssStyle(label, 'font-weight') || 'normal';
        div.textContent = label.textContent;
        const paddingRight = getCssStyle(label, 'padding-right') || '0';
        const width = getCssStyle(div, 'width');
        maxWidth = Math.max(maxWidth, parseFloat(width) + parseFloat(paddingRight));
      }
      document.body.removeChild(div);

      maxWidth = Math.ceil(maxWidth);

      for (const label of labels) {
        label.style.width = `${maxWidth}px`;
        const content = label.parentElement?.getElementsByClassName?.('bk-form-content')?.[0] as HTMLDivElement;
        if (content) {
          content.style.marginLeft = `${maxWidth}px`;
        }
      }
    }
  };

  onMounted(() => {
    if (props.autoLabelWidth) {
      calcLableWidth();

      const observer = new MutationObserver(debounce(calcLableWidth, 40));

      observer.observe(dbFormRef.value.$el, {
        subtree: true,
        childList: true,
      });

      onBeforeMount(() => {
        observer.disconnect();
      });
    }
  });

  defineExpose({
    validate: (fields: string) => dbFormRef.value.validate(fields)
      .catch((error: Error) => {
        dbFormRef.value.$el.querySelector('.bk-form-item.is-error').scrollIntoView();
        return Promise.reject(error);
      }),
    clearValidate: () => dbFormRef.value.clearValidate(),
  });
</script>

