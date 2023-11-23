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
    ref="scrollBox"
    class="scroll-faker"
    :class="{
      [`theme-${theme}`]: theme,
    }"
    :style="boxState.styles"
    @mouseenter="handleCalcScroller">
    <div
      ref="scrollContent"
      class="scroll-faker-content"
      @mouseenter="handleContentMouseenter"
      @mouseleave="handleContentMouseleave"
      @scroll="handleContentScroll">
      <slot />
    </div>
    <div
      v-if="boxState.isRenderVerticalScroll"
      ref="verticalScroll"
      class="scrollbar-vertical"
      @mouseenter="handleVerticalMouseenter"
      @mouseleave="handleVerticalMouseleave"
      @scroll="handleVerticalScroll">
      <div
        class="scrollbar-inner"
        :style="{ height: `${boxState.contentScrollHeight}px` }">
          &nbsp;
      </div>
    </div>
    <div
      v-if="boxState.isRenderHorizontalScrollbar"
      ref="horizontalScrollbar"
      class="scrollbar-horizontal"
      @mouseenter="handleHorizontalMouseenter"
      @mouseleave="handleHorizontalMouseleave"
      @scroll="handleHorizontalScroll">
      <div
        class="scrollbar-inner"
        :style="{ width: `${boxState.contentScrollWidth}px` }">
&nbsp;
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  import _ from 'lodash';
  import {
    onMounted,
    ref,
  } from 'vue';

  import useBoxState from './hooks/use-box-state';
  import useContent from './hooks/use-content';
  import useHorizotal from './hooks/use-horizotal';
  import useVertical from './hooks/use-vertical';

  export interface IContext {
    $refs: {
      scrollBox: any,
      scrollContent: any
    }
  }
</script>
<script setup lang="ts">
  interface Props{
    theme?: string
  }
  withDefaults(defineProps<Props>(), {
    theme: 'light',
  });

  const emit = defineEmits(['scroll']);

  const scrollBox = ref();
  const scrollContent = ref();
  const verticalScroll = ref();
  const horizontalScrollbar = ref();

  const {
    state: boxState,
    initState,
  } = useBoxState();

  const {
    isContentScroll,
    mouseenter: handleContentMouseenter,
    mouseleave: handleContentMouseleave,
  } = useContent();

  const {
    isVerticalScroll,
    mouseenter: handleVerticalMouseenter,
    mouseleave: handleVerticalMouseleave,
  } = useVertical();

  const {
    mouseenter: handleHorizontalMouseenter,
    mouseleave: handleHorizontalMouseleave,
  } = useHorizotal();

  // 初始化滚动状态
  const handleCalcScroller = _.throttle(initState, 100);
  // 内容区滚动
  const handleContentScroll = _.throttle((event) => {
    const {
      scrollTop,
      scrollLeft,
    } = event.target;
    if (isContentScroll.value && verticalScroll.value) {
      verticalScroll.value.scrollTo(0, scrollTop);
    }
    if (isContentScroll.value && horizontalScrollbar.value) {
      horizontalScrollbar.value.scrollLeft = scrollLeft;
    }
    emit('scroll', event);
  }, 30);
  // 垂直滚动条滚动
  const handleVerticalScroll = _.throttle((event) => {
    if (isVerticalScroll.value) {
      scrollContent.value.scrollTop = event.target.scrollTop;
    }
  }, 30);
  // 水平滚动条滚动
  const handleHorizontalScroll = _.throttle((event) => {
    if (isVerticalScroll.value) {
      scrollContent.value.scrollTop = event.target.scrollLeft;
    }
  }, 30);

  onMounted(() => {
    handleCalcScroller();
  });

  const getScroll = () => {
    const {
      scrollLeft,
      scrollTop,
    } = scrollContent.value;
    return {
      scrollLeft,
      scrollTop,
    };
  };

  const scrollTo = (scrollLeft: number, scrollTop: number) => {
    scrollContent.value.scrollTo(scrollLeft, scrollTop);
  };

  defineExpose({
    getScroll,
    scrollTo,
    boxState,
  });
</script>
<style lang='less'>
  .scroll-faker {
    position: relative;
    height: 100%;

    &:hover {
      & > .scrollbar-vertical,
      & > .scrollbar-horizontal {
        opacity: 100%;
      }
    }

    &.theme-dark {
      & > .scrollbar-vertical,
      & > .scrollbar-horizontal {
        &::-webkit-scrollbar-thumb {
          background-color: rgb(255 255 255 / 20%);
        }

        &:hover {
          &::-webkit-scrollbar-thumb {
            background-color: rgb(255 255 255 / 28%);
          }
        }
      }
    }

    & > .scroll-faker-content {
      height: 100%;
      overflow: scroll scroll;

      &::-webkit-scrollbar {
        width: 0;
        height: 0;
      }
    }

    & > .scrollbar-vertical,
    & > .scrollbar-horizontal {
      z-index: 2;
      cursor: pointer;
      opacity: 0%;
      transition: 0.15s;

      &::-webkit-scrollbar-thumb {
        background-color: rgb(151 155 165 / 80%);
        border-radius: 3px;
      }

      &:hover {
        z-index: 10000000;
        opacity: 100%;

        &::-webkit-scrollbar-thumb {
          background-color: rgb(151 155 165 / 90%);
          border-radius: 7px;
        }
      }
    }

    & > .scrollbar-vertical {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      width: 14px;
      overflow: hidden scroll;

      &::-webkit-scrollbar {
        width: 6px;
      }

      &:hover {
        &::-webkit-scrollbar {
          width: 14px !important;
        }
      }

      .scrollbar-inner {
        width: 100%;
      }
    }

    & > .scrollbar-horizontal {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      height: 14px;
      overflow: scroll hidden;

      &::-webkit-scrollbar {
        height: 6px;
      }

      &:hover {
        &::-webkit-scrollbar {
          height: 14px !important;
        }
      }

      .scrollbar-inner {
        height: 100%;
      }
    }
  }
</style>
