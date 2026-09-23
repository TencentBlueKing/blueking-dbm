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
  import { throttle } from 'lodash';
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

  // 程序设置滚动位置也会触发目标元素的 scroll 事件，记下后在该元素上忽略一次，避免内容区与滚动条来回写入
  const programmaticScrollEls = new WeakSet<HTMLElement>();

  const syncScrollPosition = (el: HTMLElement | undefined, key: 'scrollLeft' | 'scrollTop', value: number) => {
    if (!el || el[key] === value) {
      return;
    }
    const prevValue = el[key];
    el.scrollTo(key === 'scrollTop' ? { top: value } : { left: value });
    // 被浏览器钳制成原值时不会触发 scroll 事件，不能记录
    if (el[key] !== prevValue) {
      programmaticScrollEls.add(el);
    }
  };

  const handleTableContentScroll = (event: Event) => {
    const target = event.target as HTMLElement;
    if (programmaticScrollEls.delete(target)) {
      return;
    }
    syncScrollPosition(verticalScrollRef.value, 'scrollTop', target.scrollTop);
    syncScrollPosition(horizontalScrollRef.value, 'scrollLeft', target.scrollLeft);
  };

  const handleVerticalScroll = (event: Event) => {
    const target = event.target as HTMLElement;
    if (programmaticScrollEls.delete(target)) {
      return;
    }
    syncScrollPosition(tableContentEl.value, 'scrollTop', target.scrollTop);
  };

  const handleHorizontalScroll = (event: Event) => {
    const target = event.target as HTMLElement;
    if (programmaticScrollEls.delete(target)) {
      return;
    }
    syncScrollPosition(tableContentEl.value, 'scrollLeft', target.scrollLeft);
  };

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
      // 容器尺寸（如 maxHeight）变化而表格本身不变时，也要重新计算滚动条是否显示
      resizeObserver.observe(tableContentEl.value);
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
