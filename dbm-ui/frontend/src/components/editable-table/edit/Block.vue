<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    class="bk-editable-block"
    @focusin="handleFocus"
    @focusout="handleBlur">
    <div
      v-if="slots.prepend"
      class="bk-editable-block-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <div
      class="bk-editable-block-content-wrapper"
      :class="{
        'is-show-prepend': Boolean(slots.prepend),
        'is-show-append': Boolean(slots.append),
      }">
      <span ref="content">
        <slot>
          {{ modelValue }}
        </slot>
      </span>
      <div
        v-if="isShowPlacehoder"
        class="bk-editable-block-content-placeholder">
        {{ placeholder || t('请设置值') }}
      </div>
    </div>
    <div
      v-if="slots.append"
      class="bk-editable-block-append-wrapper">
      <slot name="append" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { nextTick, onMounted, onUpdated, ref, useTemplateRef, type VNode, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import useColumn from '../useColumn';

  interface Props {
    placeholder?: string;
  }

  defineProps<Props>();

  const slots = defineSlots<{
    append?: () => VNode;
    default?: () => VNode;
    prepend?: () => VNode;
  }>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const columnContext = useColumn();

  const contentRef = useTemplateRef('content');
  const isShowPlacehoder = ref(true);

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const calcPlaceholder = () => {
    nextTick(() => {
      isShowPlacehoder.value = !contentRef.value?.innerText;
    });
  };

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur');
  };

  const handleFocus = () => {
    columnContext?.focus();
  };

  onUpdated(() => {
    calcPlaceholder();
  });

  onMounted(() => {
    calcPlaceholder();
  });
</script>
<style lang="less">
  .bk-editable-block {
    position: relative;
    display: flex;
    width: 100%;
    min-height: 40px;
    align-items: center;
    overflow: hidden;

    * {
      pointer-events: all !important;
    }
  }

  .bk-editable-block-prepend-wrapper,
  .bk-editable-block-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-block-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-block-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }

  .bk-editable-block-content-wrapper {
    position: relative;
    width: 100%;
    min-height: 40px;
    padding: 10px 0;
    margin: 0 10px;
    overflow: hidden;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;

    &.is-show-prepend {
      margin-left: 0;
    }

    &.is-show-append {
      margin-right: 0;
    }
  }

  .bk-editable-block-content-placeholder {
    position: absolute;
    display: flex;
    height: 40px;
    overflow: hidden;
    font-size: 12px;
    color: #c4c6cc;
    text-overflow: ellipsis;
    white-space: nowrap;
    user-select: none;
    align-items: center;
    inset: 0;
  }
</style>
