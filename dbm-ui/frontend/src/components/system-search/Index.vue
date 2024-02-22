<template>
  <div
    ref="rootRef"
    class="dbm-system-search"
    data-role="db-system-search"
    :style="styles"
    v-bind="$attrs">
    <BkInput
      v-model="serach"
      class="search-input"
      clearable
      :placeholder="t('全站搜索 Ctrl + K')"
      type="search"
      @click="handleClick"
      @enter="handleEnter" />
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
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    computed,
    onBeforeUnmount,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import SearchResult from './components/search-result/Index.vue';
  import SearchHistory from './components/SearchHistory.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const serach = useDebouncedRef('');

  const rootRef = ref<HTMLElement>();
  const popRef = ref();
  const searchResultRef = ref();
  const isFocused = ref(false);
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);

  const styles = computed(() => ({
    flex: isFocused.value ? '1' : '0 0 auto',
  }));

  let tippyIns:Instance | undefined;

  const handleClick = () => {
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
        const dateRole = target.getAttribute('data-role');
        if (dateRole && dateRole === 'db-system-search') {
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
    handleClick();
  };

  const handleEnter = () => {
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
    transition: all .1s;

    @media screen and (max-width: 1450px) {
      flex: 1 !important;
      width: auto !important;
    }

    .search-input{
      overflow: hidden;
      border: 1px solid transparent;
      border-radius: 2px;

      .bk-input--text,
      .bk-input--suffix-icon{
        background: #303D55;
        border-radius: none;
      }

      .bk-input--text{
        color: #fff;

        &::placeholder{
          color: #929BB2;
        }
      }
    }
  }

  [data-tippy-root] .tippy-box[data-theme~="system-search-popover-theme"]{
    .tippy-content{
      padding: 0 !important;
    }
  }
</style>
