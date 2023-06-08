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
    class="main-page">
    <div
      class="main-page-list"
      :style="{
        width: renderWidth + 'px'
      }">
      <slot
        :drag-trigger="handleUserTrigger"
        :is-collapse-right="isCollapseRight"
        name="list"
        :render-width="renderWidth" />
      <DbDragResize
        :class="{
          'is-collapse-left': isCollapseLeft,
          'is-collapse-right': isCollapseRight
        }"
        :max-width="10000"
        :min-width="dragState.minWidth"
        :show-trigger="hasDetails"
        @move="handleDragMove"
        @trigger="handleDragTrigger" />
    </div>
    <div
      v-if="hasDetails"
      class="main-page-details">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useMainViewStore, useMenu } from '@stores';

  import DbDragResize from '@components/db-drag-resize/index.vue';

  import { random } from '@utils';

  interface Props {
    hasDetails: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    hasDetails: false,
  });

  const menuStore = useMenu();
  const mainViewStore = useMainViewStore();

  mainViewStore.hasPadding = false;
  const storageKey = 'DBM_DRAG_RESIZE_MANAGE';
  const storageDragState = JSON.parse(localStorage.getItem(storageKey) ?? '{}');
  const refreshMaxWidth = ref(random());
  const dragState = reactive({
    width: storageDragState?.width || 456,
    left: storageDragState?.left || 456,
    minWidth: 456,
    minWidthRight: 640,
  });
  const maxWidth = computed(() => {
    if (refreshMaxWidth.value) {
      return window.innerWidth - (menuStore.collapsed ? 60 : 260);
    }
    return 10000;
  });

  const isCollapseLeft = computed(() => dragState.width === 0);
  const isCollapseRight = computed(() => dragState.width === maxWidth.value);
  const renderWidth = computed<number>(() => (props.hasDetails ? dragState.width : maxWidth.value));

  const handleDragMove = (left: number, swipeRight: boolean, cancelFn: () => void) => {
    if (left > maxWidth.value - dragState.minWidthRight) {
      dragState.width = swipeRight ? maxWidth.value : maxWidth.value - dragState.minWidthRight;
      nextTick(cancelFn);
    } else if (left < dragState.minWidth)  {
      dragState.width = swipeRight ? dragState.minWidth : 0;
      nextTick(cancelFn);
    } else {
      dragState.width = left;
    }

    dragState.left = swipeRight
      ? Math.min(left, maxWidth.value - dragState.minWidthRight)
      : Math.max(left, dragState.minWidth);
  };

  const handleDragTrigger = (isLeft: boolean) => {
    const {
      width,
      left,
      minWidth,
    } = dragState;
    // 是否在左侧最小值与右侧最小值之间
    const withinTheZone = left >= minWidth && left <= maxWidth.value - dragState.minWidthRight;
    if (isLeft) {
      if (dragState.width === maxWidth.value) {
        dragState.width = withinTheZone ? left : maxWidth.value - dragState.minWidthRight;
      } else {
        dragState.width = 0;
      }
    } else {
      if (width === 0) {
        dragState.width = withinTheZone ? left : minWidth;
      } else {
        dragState.width = maxWidth.value;
      }
    }
  };

  const handleUserTrigger = () => {
    const {
      left,
      minWidth,
    } = dragState;
    // 是否在左侧最小值与右侧最小值之间
    const withinTheZone = left >= minWidth && left <= maxWidth.value - dragState.minWidthRight;
    dragState.width = withinTheZone ? left : maxWidth.value - dragState.minWidthRight;
  };

  const handleWindowResize = () => {
    const isCollapseRightClone = isCollapseRight.value;
    refreshMaxWidth.value = random();
    nextTick(() => {
      if (isCollapseRightClone || dragState.width > (maxWidth.value - dragState.minWidthRight)) {
        dragState.width = maxWidth.value;
        return;
      }
    });
  };

  const handleUnload = () => {
    const data = JSON.stringify({
      width: dragState.width,
      left: dragState.left,
    });
    localStorage.setItem(storageKey, data);
    window.removeEventListener('resize', handleWindowResize);
  };

  onMounted(() => {
    window.addEventListener('resize', handleWindowResize);

    window.onbeforeunload = handleUnload;
  });

  onBeforeUnmount(handleUnload);
</script>

<style lang="less" scoped>
.main-page {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  align-items: center;

  .main-page-list {
    height: 100%;
  }

  .main-page-details {
    width: 0;
    height: 100%;
    background-color: white;
    flex: 1;
  }

  :deep(.db-drag-resize) {
    &.is-collapse-left {
      .resize-trigger-right {
        color: white;
        background-color: @bg-primary;
        border-color: @border-primary;
      }
    }

    &.is-collapse-right {
      .resize-trigger-left {
        color: white;
        background-color: @bg-primary;
        border-color: @border-primary;
      }

      .drag-wrapper {
        display: none;
      }
    }
  }
}
</style>
