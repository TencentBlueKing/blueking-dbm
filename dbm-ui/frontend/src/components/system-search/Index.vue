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
      :placeholder="t('不清楚 DB 所属业务？试试全站搜索（支持域名 / IP，回车直达结果页）')"
      :show-overflow-tooltips="false"
      :type="isFocused ? 'text' : 'search'"
      @enter="handleEnter"
      @focus="handleFocus"
      @paste="handlePaste">
      <template #prefix>
        <FilterTypeSelect
          v-model="formData.filter_type"
          icon-type="down-big"
          title-color="#fff"
          trigger-class-name="system-search-top-filter-type-select" />
      </template>
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
      v-model="serach"
      @to-result="handleTypeRedirect">
      <SearchHistory
        v-if="!serach"
        v-model="serach" />
    </SearchResult>
  </div>
</template>
<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, onBeforeUnmount, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { quickSearch } from '@services/source/quickSearch';

  import { useSystemSearchStore } from '@stores';

  import { systemSearchCache } from '@common/cache';
  import { batchSplitRegex } from '@common/regex';

  import { buildURLParams } from '@utils';

  import FilterTypeSelect from './components/FilterTypeSelect.vue';
  import SearchResult from './components/search-result/Index.vue';
  import SearchHistory from './components/SearchHistory.vue';
  import useKeyboard from './hooks/useKeyboard';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const systemSearchStore = useSystemSearchStore();

  let tippyIns: Instance | undefined;

  const { formData, keyword: serach } = storeToRefs(systemSearchStore);

  const rootRef = ref<HTMLElement>();
  const popRef = ref();
  const searchResultRef = ref<InstanceType<typeof SearchResult>>();
  const isFocused = ref(false);
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);

  const styles = computed(() => ({
    flex: isFocused.value ? '1' : '0 0 auto',
  }));

  const { activeIndex } = useKeyboard(rootRef, popRef);

  const handlePaste = () => {
    setTimeout(() => {
      serach.value = serach.value.replace(/\s*:\s*/g, ':').replace(batchSplitRegex, '|');
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
          width: `${Math.max(width, 700)}px`,
        };
        tippyIns.show();
      }
    }, 200);
  };

  // 关闭弹层
  const handleOutClick = (event: MouseEvent) => {
    const eventPath = event.composedPath();
    // eslint-disable-next-line @typescript-eslint/prefer-for-of
    for (let i = 0; i < eventPath.length; i++) {
      const target = eventPath[i] as HTMLElement;
      if (target.parentElement) {
        const dataRole = target.getAttribute('data-role');
        if (dataRole && dataRole === 'db-system-search') {
          return;
        }
      }
    }
    if (tippyIns) {
      tippyIns.hide();
    }
  };

  const handleQuickKeyShow = (event: KeyboardEvent) => {
    if (!event.ctrlKey || event.key !== 'k') {
      return;
    }
    rootRef.value!.querySelector('input')!.focus();
  };

  const isQuickSearchPage = computed(() => route.name === 'QuickSearch');

  const getURLParams = (options: {
    bk_biz_ids: number[];
    db_types: string[];
    filter_type: string;
    from: string;
    resource_types: string[];
    short_code?: string;
  }) => {
    const query = Object.keys(options).reduce((prevQuery, optionKey) => {
      const optionItem = options[optionKey as keyof typeof options];

      if (optionItem !== '' && !(Array.isArray(optionItem) && optionItem.length === 0)) {
        return {
          ...prevQuery,
          [optionKey]: Array.isArray(optionItem) ? optionItem.join(',') : optionItem,
        };
      }

      return prevQuery;
    }, {});

    return buildURLParams(query);
  };

  const handleSearch = () => {
    // 空输入静默拦截
    if (!serach.value) {
      return;
    }

    const keyword = serach.value;

    // 记录搜索历史
    systemSearchCache.appendItem(keyword);

    // 判断当前是否在结果页
    if (isQuickSearchPage.value && keyword) {
      // 在结果页时，通过 store 触发刷新
      systemSearchStore.triggerRefresh(keyword);
      return;
    }

    // 非结果页，新开 Tab
    if (keyword) {
      quickSearch({
        ...formData.value,
        keyword,
      }).then((quickSearchResult) => {
        const options = {
          ...formData.value,
          from: route.name as string,
          short_code: quickSearchResult.short_code,
        };
        handleRedirect(getURLParams(options));
      });
    }
  };

  const handleRedirect = (query: string) => {
    const url = router.resolve({
      name: 'QuickSearch',
    });
    window.open(`${url.href}?${query}`, '_blank');
  };

  const handleTypeRedirect = (resourceType: string) => {
    const params = {
      ...formData.value,
      tabName: resourceType,
    };
    quickSearch({
      ...params,
      keyword: serach.value,
    }).then((quickSearchResult) => {
      const options = {
        ...params,
        from: route.name as string,
        short_code: quickSearchResult.short_code,
      };
      handleRedirect(getURLParams(options));
    });
  };

  const handleEnter = () => {
    if (activeIndex.value > -1) {
      return;
    }
    // 空输入静默拦截
    if (!serach.value) {
      return;
    }
    handleSearch();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: false,
      content: popRef.value,
      hideOnClick: false,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 4],
      onHidden() {
        isFocused.value = false;
        isPopMenuShow.value = false;
      },
      onShow() {
        isPopMenuShow.value = true;
      },
      placement: 'bottom',
      theme: 'light system-search-popover-theme',
      trigger: 'manual',
      zIndex: 999,
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

    .system-search-top-filter-type-select {
      display: flex;
      width: 80px;
      height: 30px;
      color: #fff;
      cursor: pointer;
      background: #3b4b68;
      align-items: center;
      justify-content: space-around;

      .label-content {
        position: relative;

        .more-icon {
          display: inline-block;
          font-size: 14px;
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
