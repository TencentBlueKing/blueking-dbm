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
      :placeholder="t('请输入关键字')"
      type="search"
      @click="handleClick" />
  </div>
  <div
    ref="popRef"
    data-role="db-system-search"
    :style="popContentStyle">
    <SearchResult
      v-if="isPopMenuShow"
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

  const rootRef = ref<HTMLElement>();
  const popRef = ref();
  const serach = useDebouncedRef('');
  const isFocused = ref(false);
  const popContentStyle = ref({});
  const isPopMenuShow = ref(false);

  const styles = computed(() => ({
    flex: isFocused.value ? '1' : '0 0 380px',
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


  const destroyTippy = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
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
  });

  onBeforeUnmount(() => {
    destroyTippy();
    document.body.removeEventListener('click', handleOutClick);
  });
</script>
<style lang="less">
  .dbm-system-search {
    display: block;
    width: 380px;
    max-width: 700px;
    transition: all .1s;
    flex: 1;

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
