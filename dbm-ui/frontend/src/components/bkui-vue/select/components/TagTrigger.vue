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
  <div
    class="dbm-select-tag"
    :class="{
      'has-prefix': !!$slots.prefix,
      'is-collapse-tag': collapseTags,
      'is-disabled': disabled,
      'is-simplicity': behavior === 'simplicity',
    }">
    <slot name="prefix" />
    <div
      ref="tagWrapperRef"
      class="dbm-select-tag-wrapper">
      <slot :selected="selected">
        <DbTag
          v-for="(item, index) in selected"
          :key="item.value"
          class="dbm-select-tag-item"
          closable
          :stop-propagation="false"
          :style="{ display: isTagHidden(index) ? 'none' : '' }"
          :theme="tagTheme"
          @close="handleRemoveTag(item, $event)">
          <slot
            name="tagRender"
            v-bind="item">
            {{ item.label }}
          </slot>
        </DbTag>
        <DbTag
          v-bk-tooltips="{
            content: overflowContent,
            disabled: !overflowContent,
          }"
          class="dbm-select-tag-item dbm-select-overflow-tag"
          :style="{ display: overflowTagIndex === null ? 'none' : '' }">
          +{{ selected.length - (overflowTagIndex ?? 0) }}
        </DbTag>
      </slot>
      <input
        ref="inputRef"
        class="dbm-select-tag-input"
        :disabled="disabled"
        :placeholder="selected.length ? '' : placeholder"
        :readonly="!filterable"
        :style="{ display: selected.length && !filterable ? 'none' : '' }"
        type="text"
        :value="filterable ? modelValue : ''"
        @input="handleInput"
        @keydown="handleKeydown" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { debounce } from 'lodash';
  import type { VNode } from 'vue';

  import DbTag from '@components/bkui-vue/tag/Index.vue';

  import type { SelectedItem } from '../common';

  interface Props {
    behavior?: 'normal' | 'simplicity';
    /** 溢出的标签合并为 +N 展示 */
    collapseTags?: boolean;
    disabled?: boolean;
    /** 是否允许在标签区输入内容（搜索 / 自定义创建） */
    filterable?: boolean;
    placeholder?: string;
    selected?: SelectedItem[];
    tagTheme?: '' | 'danger' | 'info' | 'success' | 'warning';
  }

  interface Emits {
    (e: 'enter', value: string, event: KeyboardEvent): void;
    (e: 'remove', value: SelectedItem['value']): void;
  }

  interface Exposes {
    blur: () => void;
    focus: () => void;
  }

  defineOptions({
    name: 'SelectTagTrigger',
  });

  const props = withDefaults(defineProps<Props>(), {
    behavior: 'normal',
    collapseTags: false,
    disabled: false,
    filterable: false,
    placeholder: '',
    selected: () => [],
    tagTheme: '',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    default?: (props: { selected: SelectedItem[] }) => VNode;
    prefix?: () => VNode;
    tagRender?: (props: SelectedItem) => VNode;
  }>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const tagWrapperRef = useTemplateRef('tagWrapperRef');
  const inputRef = useTemplateRef('inputRef');

  const overflowTagIndex = ref<null | number>(null);

  const overflowContent = computed(() => {
    if (overflowTagIndex.value === null) {
      return '';
    }
    return props.selected
      .slice(overflowTagIndex.value)
      .map((item) => item.label)
      .join(', ');
  });

  const isTagHidden = (index: number) => overflowTagIndex.value !== null && index >= overflowTagIndex.value;

  const getTagElements = () =>
    Array.from(tagWrapperRef.value?.querySelectorAll<HTMLElement>('.dbm-select-tag-item') ?? []).filter(
      (el) => !el.classList.contains('dbm-select-overflow-tag'),
    );

  /**
   * 计算折叠位置：先还原全部标签，再找出第一个换行的标签作为折叠起点。
   * 若 +N 标签本身被挤到第二行，则再少展示一个标签。
   */
  const calcOverflow = async () => {
    if (!props.collapseTags) {
      overflowTagIndex.value = null;
      return;
    }
    overflowTagIndex.value = null;
    await nextTick();
    const tagElements = getTagElements();
    const wrappedIndex = tagElements.findIndex(
      (tagElement, index) => index > 0 && tagElements[index - 1].offsetTop !== tagElement.offsetTop,
    );
    if (wrappedIndex <= 0) {
      return;
    }
    overflowTagIndex.value = wrappedIndex;
    await nextTick();
    const overflowTagElement = tagWrapperRef.value?.querySelector<HTMLElement>('.dbm-select-overflow-tag');
    if (overflowTagElement && overflowTagElement.offsetTop !== tagElements[0].offsetTop && wrappedIndex > 1) {
      overflowTagIndex.value = wrappedIndex - 1;
    }
  };

  const debouncedCalcOverflow = debounce(calcOverflow, 150);

  let resizeObserver: ResizeObserver | undefined;

  watch([() => props.selected, () => props.collapseTags], calcOverflow, {
    deep: true,
    flush: 'post',
  });

  onMounted(() => {
    calcOverflow();
    if (tagWrapperRef.value) {
      resizeObserver = new ResizeObserver(debouncedCalcOverflow);
      resizeObserver.observe(tagWrapperRef.value);
    }
  });

  onBeforeUnmount(() => {
    debouncedCalcOverflow.cancel();
    resizeObserver?.disconnect();
    resizeObserver = undefined;
  });

  const handleRemoveTag = (item: SelectedItem, event: MouseEvent) => {
    // 删除标签不应触发外层 trigger 的展开 / 收起
    event.stopPropagation();
    if (props.disabled) {
      return;
    }
    emits('remove', item.value);
  };

  const handleInput = (event: Event) => {
    modelValue.value = (event.target as HTMLInputElement).value;
  };

  const handleKeydown = (event: KeyboardEvent) => {
    if (event.code === 'Enter' || event.code === 'NumpadEnter') {
      emits('enter', (event.target as HTMLInputElement).value, event);
    }
  };

  defineExpose<Exposes>({
    blur() {
      inputRef.value?.blur();
    },
    focus() {
      inputRef.value?.focus();
    },
  });
</script>

<style lang="less">
  .dbm-select-tag {
    display: flex;
    width: 100%;
    min-height: 32px;
    padding: 0 28px 0 10px;
    color: #63656e;
    cursor: pointer;
    background-color: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    box-sizing: border-box;
    align-items: center;
    transition: all 0.1s;

    &:not(.is-collapse-tag) {
      position: relative;
      z-index: 1;
      height: auto;
      flex-wrap: wrap;
    }

    &.is-collapse-tag {
      height: 32px;
      overflow: hidden;

      .dbm-select-tag-wrapper {
        height: 30px;
      }
    }

    &.has-prefix {
      padding-left: 0;
    }

    &:not(.is-disabled, .is-simplicity):hover {
      border-color: #979ba5;
    }

    &.is-disabled {
      cursor: not-allowed;
      background-color: #fafbfd;
      border-color: #dcdee5;

      .dbm-select-tag-input {
        cursor: not-allowed;
      }

      .dbm-tag {
        cursor: not-allowed;

        &:hover {
          background-color: #f0f1f5;
        }
      }
    }

    &.is-simplicity {
      background-color: transparent;
      border-color: transparent;
      border-bottom-color: #c4c6cc;

      &:hover {
        background-color: #f5f7fa;
        border-color: transparent;
        border-bottom-color: #c4c6cc;
        box-shadow: none;
      }
    }

    .dbm-select-tag-wrapper {
      display: flex;
      width: 100%;
      padding: 4px 0;
      overflow: hidden;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
    }

    .dbm-tag.dbm-select-tag-item {
      max-width: 190px;
      padding: 0 4px;
      margin: 0;
    }

    .dbm-select-overflow-tag {
      cursor: pointer;
    }

    .dbm-select-tag-input {
      width: 1%;
      height: 22px;
      padding: 0;
      margin: 0 5px 0 0;
      overflow: hidden;
      font-size: 12px;
      color: #63656e;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      background-color: transparent;
      border: none;
      outline: none;
      flex-grow: 1;

      &::placeholder {
        color: #c4c6cc;
      }
    }
  }
</style>
