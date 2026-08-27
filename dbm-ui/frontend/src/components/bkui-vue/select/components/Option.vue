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
  <li
    v-show="registry.visible"
    ref="rootRef"
    v-bk-tooltips="{
      content: disabledTips,
      disabled: !disabledTips,
      placement: 'right',
    }"
    class="dbm-select-option"
    :class="{
      'is-disabled': isDisabled,
      'is-hover': isHover,
      'is-multiple': multiple,
      'is-selected': isSelected,
    }"
    @click="handleOptionClick"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave">
    <BkCheckbox
      v-if="showSelectedIcon"
      class="dbm-select-checkbox"
      :disabled="isDisabled"
      :model-value="isSelected" />
    <slot>
      <span
        class="dbm-select-option-item"
        :title="String(optionName)">
        <template v-if="keywordSegments">
          <span
            v-for="(segment, index) in keywordSegments"
            :key="index"
            :class="{ 'is-keyword': segment.isKeyword }">
            {{ segment.text }}
          </span>
        </template>
        <template v-else>{{ optionName }}</template>
      </span>
    </slot>
  </li>
</template>

<script setup lang="ts">
  import { isEqual } from 'lodash';
  import type { VNode } from 'vue';

  import { optionGroupKey, type OptionValue, selectKey } from '../common';

  interface Props {
    /** 支持 boolean 与 { disabled, tips } 两种配置，后者可在禁用时给出原因 */
    disabled?: boolean | { disabled: boolean; tips: string };
    id?: OptionValue;
    /** name 的别名，兼容 bk-option 的 label 用法 */
    label?: number | string;
    name?: number | string;
    order?: number;
    /** 虚拟滚动下跳过注册，避免滚动过程频繁 register / unregister */
    skipRegister?: boolean;
    /** id 的别名，兼容 bk-option 的 value 用法 */
    value?: OptionValue;
  }

  defineOptions({
    name: 'Option',
  });

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    id: undefined,
    label: undefined,
    name: undefined,
    order: 0,
    skipRegister: false,
    value: undefined,
  });

  defineSlots<{
    default?: () => VNode;
  }>();

  const select = inject(selectKey, null);
  const group = inject(optionGroupKey, null);

  const rootRef = useTemplateRef('rootRef');

  const optionID = computed(() => (props.id !== undefined ? props.id : props.value));

  const optionName = computed(() => {
    if (props.name !== undefined) {
      return props.name;
    }
    return props.label !== undefined ? props.label : optionID.value;
  });

  const isDisabled = computed(() => {
    // 所在分组被禁用时，分组内选项一律不可选
    if (group?.disabled) {
      return true;
    }
    return typeof props.disabled === 'boolean' ? props.disabled : (props.disabled?.disabled ?? false);
  });

  const disabledTips = computed(() => (typeof props.disabled === 'boolean' ? '' : (props.disabled?.tips ?? '')));

  const multiple = computed(() => !!select?.multiple);

  // 多选用 checkbox 表示选中，单选靠整行高亮，不额外展示图标
  const showSelectedIcon = computed(() => !!select?.showSelectedIcon && multiple.value);

  // 选项值可能是对象，引用变化后仍需正确回显，统一用 isEqual 比较
  const isSelected = computed(() => !!select?.selected.some((item) => isEqual(item.value, optionID.value)));

  const isHover = computed(() => select?.activeOptionValue === optionID.value);

  // 搜索命中时把展示文案拆成「命中 / 未命中」片段，用于关键字高亮
  const keywordSegments = computed(() => {
    if (!select?.highlightKeyword) {
      return null;
    }
    const keyword = select.curSearchValue.trim();
    const text = String(optionName.value);
    const lowerText = text.toLowerCase();
    const lowerKeyword = keyword.toLowerCase();
    if (!keyword || !lowerText.includes(lowerKeyword)) {
      return null;
    }
    const segments: { isKeyword: boolean; text: string }[] = [];
    let cursor = 0;
    let matchIndex = lowerText.indexOf(lowerKeyword);
    while (matchIndex > -1) {
      if (matchIndex > cursor) {
        segments.push({ isKeyword: false, text: text.slice(cursor, matchIndex) });
      }
      segments.push({ isKeyword: true, text: text.slice(matchIndex, matchIndex + keyword.length) });
      cursor = matchIndex + keyword.length;
      matchIndex = lowerText.indexOf(lowerKeyword, cursor);
    }
    if (cursor < text.length) {
      segments.push({ isKeyword: false, text: text.slice(cursor) });
    }
    return segments;
  });

  const registry = reactive({
    getEl: () => rootRef.value,
    isDisabled,
    optionID,
    optionName,
    order: computed(() => props.order),
    visible: true,
  });

  // 记录实际的注册状态：skipRegister 会随虚拟滚动开关变化，注销时不能再现读该 prop，否则会残留已注册的选项
  let isRegistered = false;

  const register = () => {
    if (props.skipRegister) {
      return;
    }
    select?.register(registry.optionID, registry);
    group?.register(registry.optionID, registry);
    isRegistered = true;
  };

  const unregister = (key: OptionValue) => {
    if (!isRegistered) {
      return;
    }
    select?.unregister(key, registry);
    group?.unregister(key, registry);
    isRegistered = false;
  };

  // 选项值变化时重新注册，避免 optionsMap 中残留旧值
  watch(optionID, (value, oldValue) => {
    unregister(oldValue);
    register();
  });

  onBeforeMount(register);

  onBeforeUnmount(() => {
    unregister(registry.optionID);
  });

  const handleOptionClick = () => {
    if (isDisabled.value) {
      return;
    }
    select?.handleOptionSelected(registry);
  };

  const handleMouseEnter = () => {
    select?.setActiveOptionValue(registry.optionID);
  };

  const handleMouseLeave = () => {
    select?.setActiveOptionValue('');
  };
</script>

<style lang="less">
  .dbm-select-option {
    position: relative;
    display: flex;
    min-height: 32px;
    padding: 0 12px;
    overflow: hidden;
    color: #63656e;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    align-items: center;

    &.is-hover,
    &:hover {
      color: #63656e;
      background-color: #f5f7fa;
    }

    &.is-selected:not(.is-multiple) {
      color: #3a84ff;
      background-color: #e1ecff;
    }

    &.is-disabled {
      color: #c4c6cc;
      cursor: not-allowed;
      background-color: transparent;
    }

    &.is-multiple {
      &.is-selected {
        background-color: #fff;
      }

      &.is-hover,
      &:hover {
        background-color: #f5f7fa;
      }
    }

    .dbm-select-option-item {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;

      .is-keyword {
        display: inline-flex;
        color: #3a84ff;
      }
    }

    .dbm-select-checkbox {
      margin-right: 6px;
      pointer-events: none;

      .bk-checkbox-original {
        opacity: 0%;
      }
    }
  }
</style>
