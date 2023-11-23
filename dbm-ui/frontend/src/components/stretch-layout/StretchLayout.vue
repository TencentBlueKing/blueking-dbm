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
    class="stretch-layout"
    :data-name="name">
    <div
      class="stretch-layout-left"
      :style="{
        width: `${renderLeftWidth}px`
      }">
      <slot name="list" />
    </div>
    <DragResize
      :show-trigger="isShowTrigger"
      :style="{
        left: `${renderLeftWidth-1}px`
      }"
      @change="handleLeftWidthChange"
      @open="handleOpenChange" />
    <div
      v-if="isShowTrigger"
      class="stretch-layout-right">
      <slot name="right" />
    </div>
  </div>
</template>
<script lang="ts">
  import {
    type InjectionKey,
    provide,
    type Ref,
  } from 'vue';

  export const provideKey: InjectionKey<{
    isOpen: Ref<boolean>,
    splitScreen: () => void
  }> = Symbol.for('stretch-layout');
</script>
<script setup lang="ts">
  import { readonly } from 'vue';

  import DragResize from './components/DragResize.vue';

  interface Props {
    name: string,
    minLeftWidth?: number
  }

  const props = withDefaults(defineProps<Props>(), {
    minLeftWidth: 456,
  });

  defineSlots<{
    list(): any,
    default(): any,
    right(): any,
  }>();

  const rootRef = ref();
  const isShowTrigger = ref(false);
  const isOpen = ref(false);
  const renderLeftWidth = ref(0);

  const getMaxWidth = () => rootRef.value.getBoundingClientRect().width;
  // 拖动改变左侧宽度
  const handleLeftWidthChange = (newLeftWidth: number) => {
    const maxWidth = getMaxWidth();
    if (newLeftWidth < 100) {
      isOpen.value = false;
      renderLeftWidth.value = 0;
    } else if (newLeftWidth > maxWidth - 100) {
      isOpen.value = false;
      renderLeftWidth.value = maxWidth;
    } else {
      renderLeftWidth.value = newLeftWidth;
    }
  };

  // 切换展开收起
  const handleOpenChange = (direction: string) => {
    renderLeftWidth.value = isOpen.value ? 0 : props.minLeftWidth;
    if (isOpen.value) {
      renderLeftWidth.value = direction === 'left' ? 0 : getMaxWidth();
    } else {
      renderLeftWidth.value = props.minLeftWidth;
    }
    isOpen.value = !isOpen.value;
  };

  // 拖拽改变浏览器大小
  const handleWindowResize = () => {
    if (!isOpen.value) {
      renderLeftWidth.value = renderLeftWidth.value === 0 ? 0 : getMaxWidth();
    }
  };

  provide(provideKey, {
    isOpen: readonly(isOpen),
    splitScreen() {
      isShowTrigger.value = true;
      if (isOpen.value) {
        return;
      }
      handleOpenChange('left');
    },
  });

  onMounted(() => {
    if (!isOpen.value) {
      renderLeftWidth.value = getMaxWidth();
    }
    window.addEventListener('resize', handleWindowResize);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleWindowResize);
  });
</script>

<style lang="less">
.stretch-layout {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;

  .stretch-layout-right {
    width: 0;
    flex: 1;
  }
}
</style>
