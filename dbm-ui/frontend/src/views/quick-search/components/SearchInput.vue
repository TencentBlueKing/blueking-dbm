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
    class="search-input"
    data-role="quick-search-result">
    <FilterTypeSelect
      v-model="filterType"
      icon-type="down-big"
      title-color="#4d4f56"
      trigger-class-name="system-search-result-filter-type-select" />
    <div
      ref="rootRef"
      class="input-box">
      <BkInput
        v-model="modelValue"
        autosize
        class="search-input-textarea"
        clearable
        :placeholder="t('全站搜索，支持多对象，Shift + Enter 换行，Enter键开启搜索')"
        :resize="false"
        type="textarea"
        @blur="handleBlur"
        @enter="handleEnter"
        @focus="handleFocus"
        @paste="handlePaste" />
    </div>
    <BkButton
      class="search-input-icon"
      size="large"
      theme="primary"
      @click="handleSearch">
      <DbIcon
        class="mr-8"
        type="search" />
      {{ t('搜索') }}
    </BkButton>
  </div>
  <div
    ref="popRef"
    data-role="db-system-search-result"
    :style="popContentStyle">
    <SearchResult
      v-if="isPopMenuShow"
      v-model="modelValue"
      :filter-type="filterType"
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

  import FilterTypeSelect from '@components/system-search/components/FilterTypeSelect.vue';
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
  const filterType = defineModel<string>('filter-type', {
    default: '',
  });

  const { t } = useI18n();

  let tippyIns: Instance | undefined;

  const rootRef = ref<HTMLElement>();
  const popRef = ref<HTMLElement>();
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);
  const isFocused = ref(false);

  useKeyboard(rootRef, popRef, 'textarea');

  watch([modelValue, isFocused], () => {
    setTimeout(() => {
      if (tippyIns && isFocused.value) {
        tippyIns.setProps({
          // offset: modelValue.value.includes('\n') ? getTippyInsOffset() : [0, 8],
          offset: getTippyInsOffset(),
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
      modelValue.value = modelValue.value.replace(batchSplitRegex, '\n');
    });
  };

  const handleFocus = () => {
    modelValue.value = modelValue.value.replace(/\|/g, '\n');
    isFocused.value = true;

    const { width } = rootRef.value!.getBoundingClientRect();
    if (tippyIns) {
      popContentStyle.value = {
        width: `${Math.max(width - 91, 712)}px`,
      };
      tippyIns.show();
    }
  };

  const handleBlur = () => {
    modelValue.value = modelValue.value.replace(/\n/g, '|');
    isFocused.value = false;
  };

  // const handleClear = () => {
  //   modelValue.value = '';
  // };

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

<style lang="less">
  // .operation-more-main {
  .system-search-result-filter-type-select {
    display: flex;
    width: 92px;
    height: 40px;
    font-size: 14px;
    cursor: pointer;
    background-color: #fafbfd;
    border: 1px solid #c4c6cc;
    border-right: none;
    border-radius: 2px 0 0 2px;
    align-items: center;
    justify-content: space-around;

    .label-content {
      position: relative;

      .more-icon {
        display: inline-block;
        font-size: 16px;
        transform: rotate(0deg);
        transition: all 0.5s;
      }

      .more-icon-active {
        transform: rotate(-180deg);
      }

      .icon-disabled {
        color: #c4c6cc;
      }
    }
  }
</style>
<style lang="less" scoped>
  .search-input {
    position: relative;
    display: flex;
    // width: 900px;
    height: 40px;

    .input-box {
      position: relative;
      width: 712px;
      height: 40px;
      flex: 1;

      .search-input-textarea {
        border-radius: 0;
      }

      :deep(.bk-textarea) {
        position: absolute;
        z-index: 10;

        textarea {
          height: 38px !important;
          min-height: 38px !important;
          padding: 12px 30px 12px 10px;
        }

        &.is-focused {
          textarea {
            max-height: 400px;
            min-height: 100px !important;
          }
        }

        .bk-textarea--clear-icon {
          position: absolute;
          top: 12px;
          right: 0;
        }
      }
    }

    .icon-area {
      .search-input-icon {
        height: 40px;
        cursor: pointer;
        border-radius: 0 2px 2px 0;
      }
    }
  }
</style>
