<template>
  <Teleport
    v-if="tableEl"
    defer
    :to="tableEl">
    <div key="t-table--scroll-container">
      <div
        v-if="isShowVerticalScroll"
        ref="verticalScrollRef"
        class="t-table--scroll-vertical"
        :style="{ top: `${verticalPositionTop}px` }"
        @scroll="handleVerticalScroll">
        <div
          class="t-table--scroll-bar"
          :style="{ height: `${scrollContentHeight}px` }">
          &nbsp;
        </div>
      </div>
      <div
        v-if="isSHowHorizontalScroll"
        ref="horizontalScrollRef"
        class="t-table--scroll-horizontal"
        @scroll="handleHorizontalScroll">
        <div
          class="t-table--scroll-bar"
          :style="{ width: `${scrollContentWidth}px` }">
          &nbsp;
        </div>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { throttle } from 'lodash-es';
  import { getCurrentInstance, onBeforeUnmount, onMounted, ref } from 'vue';

  const tableEl = ref<HTMLElement>();
  const tableContentEl = ref<HTMLElement>();

  const verticalScrollRef = ref<HTMLElement>();
  const horizontalScrollRef = ref<HTMLElement>();

  const isShowVerticalScroll = ref(false);
  const isSHowHorizontalScroll = ref(false);

  const scrollContentWidth = ref(0);
  const scrollContentHeight = ref(0);
  const verticalPositionTop = ref(0);

  const currentInstance = getCurrentInstance();

  const calcScrollStatus = throttle(() => {
    if (!tableContentEl.value) {
      return;
    }

    const { clientHeight, clientWidth, scrollHeight, scrollWidth } = tableContentEl.value as HTMLElement;
    scrollContentWidth.value = scrollWidth;
    verticalPositionTop.value =
      tableContentEl.value!.querySelector('.t-table__header')?.getBoundingClientRect().height || 0;
    scrollContentHeight.value = scrollHeight - verticalPositionTop.value;

    isShowVerticalScroll.value = scrollHeight > clientHeight;
    isSHowHorizontalScroll.value = scrollWidth > clientWidth;
  }, 20);

  const handleTableContentScroll = throttle((event: Event) => {
    const { scrollLeft, scrollTop } = event.target as HTMLElement;
    verticalScrollRef.value?.scrollTo(0, scrollTop);
    horizontalScrollRef.value?.scrollTo(scrollLeft, 0);
  }, 20);

  const handleVerticalScroll = throttle((event: Event) => {
    tableContentEl.value!.scrollTop = (event.target as HTMLElement).scrollTop;
  }, 20);

  const handleHorizontalScroll = throttle((event: Event) => {
    window.requestAnimationFrame(() => {
      tableContentEl.value!.scrollLeft = (event.target as HTMLElement).scrollLeft;
    });
  }, 20);

  let resizeObserver: ResizeObserver;
  let mutationObserver: MutationObserver;

  onMounted(() => {
    tableEl.value = currentInstance?.proxy?.$el.parentNode.querySelector('.t-table');

    mutationObserver = new MutationObserver(() => {
      tableContentEl.value = tableEl.value!.querySelector('.t-table__content') as HTMLElement;
      if (!tableContentEl.value) {
        return;
      }
      mutationObserver.disconnect();
      tableContentEl.value.addEventListener('scroll', handleTableContentScroll);
      resizeObserver = new ResizeObserver(() => {
        calcScrollStatus();
      });

      resizeObserver.observe(tableContentEl.value.querySelector('table') as HTMLElement);
    });

    mutationObserver.observe(tableEl.value as HTMLElement, {
      childList: true,
      subtree: true,
    });
  });

  onBeforeUnmount(() => {
    tableContentEl.value?.removeEventListener('scroll', handleTableContentScroll);
    resizeObserver?.disconnect();
    mutationObserver?.disconnect();
  });
</script>
