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
    ref="rootRef"
    class="search-input"
    data-role="quick-search-result">
    <BkInput
      v-model="modelValue"
      autosize
      class="search-input-textarea"
      clearable
      :placeholder="t('请输入关键字， Shift + Enter 换行')"
      :resize="false"
      type="textarea"
      @blur="handleBlur"
      @enter="handleEnter"
      @focus="handleFocus"
      @paste="handlePaste" />
    <div class="icon-area">
      <DbIcon
        v-if="modelValue"
        class="search-input-icon icon-close"
        type="close-circle-shape"
        @click="handleClear" />
      <BkButton
        class="search-input-icon ml-4"
        size="large"
        theme="primary"
        @click="handleSearch">
        <DbIcon
          class="mr-8"
          type="search" />
        {{ t('搜索') }}
      </BkButton>
    </div>
  </div>
  <div
    ref="popRef"
    data-role="db-system-search-result"
    :style="popContentStyle">
    <SearchResult
      v-if="isPopMenuShow"
      v-model="modelValue"
      :show-options="false"
      style="height: 506px">
      <SearchHistory
        v-if="!modelValue"
        v-model="modelValue" />
    </SearchResult>
  </div>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import SearchResult from '@components/system-search/components/search-result/Index.vue';
  import SearchHistory from '@components/system-search/components/SearchHistory.vue';
  import useKeyboard from '@components/system-search/hooks/useKeyboard';

  interface Emits {
    (e: 'search', value: string): void;
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  let tippyIns: Instance | undefined;

  const rootRef = ref<HTMLElement>();
  const popRef = ref<HTMLElement>();
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);

  useKeyboard(rootRef, popRef, 'textarea');

  watch(modelValue, () => {
    setTimeout(() => {
      if (tippyIns) {
        tippyIns.setProps({
          offset: modelValue.value.includes('\n') ? getTippyInsOffset() : [0, 8],
        });
      }
    });
  });

  const getTippyInsOffset = (): [number, number] => {
    const textareaList = rootRef.value!.getElementsByTagName('textarea');
    const { bottom: textareaBottom } = textareaList[0].getBoundingClientRect();
    const { bottom: rootBottom } = rootRef.value!.getBoundingClientRect();

    return [0, textareaBottom - rootBottom + 4];
  };

  const handleEnter = (value: string, event: KeyboardEvent) => {
    // shift + enter 时，悬浮撑高
    // 只按下 enter 时，进行搜索
    if (!event.shiftKey) {
      event.preventDefault();
      handleSearch();
    }
  };

  const handlePaste = () => {
    setTimeout(() => {
      modelValue.value = modelValue.value.replace(batchSplitRegex, '|');
    });
  };

  const handleFocus = () => {
    modelValue.value = modelValue.value.replace(/\|/g, '\n');

    const { width } = rootRef.value!.getBoundingClientRect();
    if (tippyIns) {
      popContentStyle.value = {
        width: `${Math.max(width - 91, 600)}px`,
      };
      tippyIns.show();
    }
  };

  const handleBlur = () => {
    modelValue.value = modelValue.value.replace(/\n/g, '|');
  };

  const handleClear = () => {
    modelValue.value = '';
  };

  const handleSearch = () => {
    if (tippyIns) {
      const textareaList = rootRef.value!.getElementsByTagName('textarea');
      textareaList[0].blur();
      tippyIns.hide();
    }
    emits('search', modelValue.value);
  };

  // 关闭弹层
  const handleOutClick = (event: MouseEvent) => {
    const eventPath = event.composedPath();
    for (let i = 0; i < eventPath.length; i++) {
      const target = eventPath[i] as HTMLElement;
      if (target.parentElement) {
        const dataRole = target.getAttribute('data-role');
        if (dataRole && dataRole === 'quick-search-result') {
          return;
        }
      }
    }
    if (tippyIns) {
      tippyIns.hide();
    }
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: () => document.body,
      theme: 'light system-search-popover-theme',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: false,
      offset: [0, 8],
      zIndex: 999,
      hideOnClick: false,
      onHidden() {
        isPopMenuShow.value = false;
      },
      onShow() {
        isPopMenuShow.value = true;
      },
    });
    document.body.addEventListener('click', handleOutClick);
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
    document.body.removeEventListener('click', handleOutClick);
  });
</script>

<style lang="less" scoped>
  .search-input {
    position: relative;
    width: 900px;
    height: 40px;

    .search-input-textarea {
      position: absolute;
      z-index: 4;
      width: 810px;

      :deep(textarea) {
        max-height: 400px;
        min-height: 40px !important;
        padding: 12px 30px 12px 10px;
      }
    }

    .icon-area {
      position: absolute;
      top: 0;
      right: 0;
      z-index: 4;

      .search-input-icon {
        height: 44px;
        cursor: pointer;
      }

      .icon-close {
        color: #c4c6cc;
        display: none;
      }
    }

    &:hover {
      .icon-close {
        display: inline-block;
      }
    }
  }
</style>
