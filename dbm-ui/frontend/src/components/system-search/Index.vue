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
    v-db-console="'globalSearch'"
    class="dbm-system-search"
    data-role="db-system-search"
    :style="styles"
    v-bind="$attrs">
    <BkInput
      v-model="serach"
      class="search-input"
      clearable
      :placeholder="t('全站搜索 Ctrl + K')"
      :type="isFocused ? 'text' : 'search'"
      @enter="handleEnter"
      @focus="handleFocus"
      @paste="handlePaste">
      <template
        v-if="isFocused"
        #suffix>
        <div class="serach-btn">
          <BkButton
            size="small"
            theme="primary"
            @click="handleSearch">
            <DbIcon
              class="mr-4"
              type="search" />
            {{ t('搜索') }}
          </BkButton>
        </div>
      </template>
    </BkInput>
  </div>
  <div
    ref="popRef"
    data-role="db-system-search"
    :style="popContentStyle">
    <SearchResult
      v-if="isPopMenuShow"
      ref="searchResultRef"
      v-model="serach">
      <SearchHistory
        v-if="!serach"
        v-model="serach" />
    </SearchResult>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, onBeforeUnmount, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import SearchResult from './components/search-result/Index.vue';
  import SearchHistory from './components/SearchHistory.vue';
  import useKeyboard from './hooks/useKeyboard';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const serach = ref('');
  const rootRef = ref<HTMLElement>();
  const popRef = ref();
  const searchResultRef = ref();
  const isFocused = ref(false);
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);

  const styles = computed(() => ({
    flex: isFocused.value ? '1' : '0 0 auto',
  }));

  const { activeIndex } = useKeyboard(rootRef, popRef);

  let tippyIns: Instance | undefined;

  const handlePaste = () => {
    setTimeout(() => {
      serach.value = serach.value.replace(batchSplitRegex, '|');
    });
  };

  const handleFocus = () => {
    if (isFocused.value) {
      return;
    }
    isFocused.value = true;

    // 输入框宽度变化有 100ms，所以这里延时一下
    setTimeout(() => {
      const { width } = rootRef.value!.getBoundingClientRect();
      if (tippyIns) {
        popContentStyle.value = {
          width: `${Math.max(width, 600)}px`,
        };
        tippyIns.show();
      }
    }, 200);
  };

  // 关闭弹层
  const handleOutClick = (event: MouseEvent) => {
    const eventPath = event.composedPath();
    for (let i = 0; i < eventPath.length; i++) {
      const target = eventPath[i] as HTMLElement;
      if (target.parentElement) {
        const dataRole = target.getAttribute('data-role');
        if (dataRole && dataRole === 'db-system-search') {
          return;
        }
      }
    }
    tippyIns && tippyIns.hide();
  };

  const handleQuickKeyShow = (event: KeyboardEvent) => {
    if (!event.ctrlKey || event.key !== 'k') {
      return;
    }
    rootRef.value!.querySelector('input')!.focus();
  };

  const handleSearch = () => {
    // 页面跳转参数处理
    const options = searchResultRef.value.getFilterOptions();
    const query = Object.keys(options).reduce((prevQuery, optionKey) => {
      const optionItem = options[optionKey];

      if (optionItem !== '' && !(Array.isArray(optionItem) && optionItem.length === 0)) {
        if (Array.isArray(optionItem)) {
          return {
            ...prevQuery,
            [optionKey]: optionItem.join(','),
          };
        }

        return {
          ...prevQuery,
          [optionKey]: optionItem,
        };
      }

      return prevQuery;
    }, {});

    const url = router.resolve({
      name: 'QuickSearch',
      query: {
        ...query,
        from: route.name as string,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleEnter = () => {
    if (activeIndex.value > -1) {
      return;
    }
    handleSearch();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-end',
      appendTo: () => document.body,
      theme: 'light system-search-popover-theme',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: false,
      offset: [0, 4],
      zIndex: 999,
      hideOnClick: false,
      onHidden() {
        isFocused.value = false;
        isPopMenuShow.value = false;
      },
      onShow() {
        isPopMenuShow.value = true;
      },
    });
    document.body.addEventListener('click', handleOutClick);
    window.addEventListener('keyup', handleQuickKeyShow);
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
    document.body.removeEventListener('click', handleOutClick);
    window.removeEventListener('keyup', handleQuickKeyShow);
  });
</script>
<style lang="less">
  .dbm-system-search {
    display: block;
    width: 380px;
    max-width: 700px;
    transition: all 0.1s;

    @media screen and (max-width: 1450px) {
      flex: 1 !important;
      width: auto !important;
    }

    .search-input {
      overflow: hidden;
      border: 1px solid transparent;
      border-radius: 2px;

      .bk-input--text,
      .bk-input--suffix-icon {
        background: #303d55;
        border-radius: 0;
      }

      .bk-input--text {
        color: #fff;
        border-radius: 0;

        &::placeholder {
          color: #929bb2;
        }
      }

      .serach-btn {
        display: flex;
        padding-right: 4px;
        background: #303d55;
        align-items: center;

        &::before {
          width: 1px;
          height: 12px;
          margin-right: 6px;
          background: #63656e;
          content: '';
        }
      }
    }
  }

  [data-tippy-root] .tippy-box[data-theme~='system-search-popover-theme'] {
    .tippy-content {
      padding: 0 !important;
    }
  }
</style>
