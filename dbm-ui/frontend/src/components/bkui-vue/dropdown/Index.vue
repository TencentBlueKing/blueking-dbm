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
    class="dbm-dropdown">
    <div
      ref="referenceRef"
      class="dbm-dropdown-reference"
      :class="{ 'is-disabled': disabled }"
      @mouseenter="handleMouseenter"
      @mouseleave="handleMouseleave">
      <slot :popover-show="isPopoverShow" />
    </div>
    <!-- 弹层内容：作为 tippy.js 挂载源，展示时被移动到 body -->
    <div style="display: none">
      <div
        ref="contentRef"
        class="dbm-dropdown-content"
        @click="hide">
        <slot
          v-if="isContentMounted"
          name="content" />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
  import tippy, { type Instance, type Placement, type SingleTarget } from 'tippy.js';
  import type { VNode } from 'vue';

  // 鼠标移出不再收起，需记录当前展开的菜单，hover 另一个下拉时将其收起，避免同屏多个菜单同时展开
  let activeHide: (() => void) | undefined;
</script>

<script setup lang="ts">
  /**
   * 交互：鼠标移入触发元素展开；点击菜单内容、点击外部时收起。
   * 鼠标移出不收起，避免菜单项触发的侧滑、二次确认被误关
   */
  export interface Props {
    disabled?: boolean;
    placement?: Placement;
  }

  type Emits = (e: 'hide' | 'show') => void;

  defineOptions({
    name: 'Dropdown',
  });

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
    placement: 'bottom',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    content?: () => VNode;
    default?: (props: { popoverShow: boolean }) => VNode;
  }>();

  // hover 展开延迟，比 bk-popover 默认的 100ms 更钝，避免鼠标划过时误弹出
  const HOVER_DELAY = 200;

  const rootRef = useTemplateRef('rootRef');
  const referenceRef = useTemplateRef('referenceRef');
  const contentRef = useTemplateRef('contentRef');

  let tippyInstance: Instance | undefined;
  let resizeObserver: ResizeObserver | undefined;
  let referenceObserver: ResizeObserver | undefined;
  let hoverTimer: ReturnType<typeof setTimeout> | undefined;

  const isPopoverShow = ref(false);
  // 首次展开才渲染内容，之后常驻：菜单项里打开的侧滑、弹窗不会因菜单收起被卸载
  const isContentMounted = ref(false);

  const show = () => {
    if (props.disabled) {
      return;
    }
    isPopoverShow.value = true;
  };

  const hide = () => {
    isPopoverShow.value = false;
  };

  const clearHoverTimer = () => {
    if (hoverTimer) {
      clearTimeout(hoverTimer);
      hoverTimer = undefined;
    }
  };

  // 移入触发元素延迟展开，中途移走则取消，避免划过时闪现
  const handleMouseenter = () => {
    clearHoverTimer();
    if (props.disabled || isPopoverShow.value) {
      return;
    }
    // 移到别的下拉上时，先收起上一个展开的菜单
    if (activeHide) {
      activeHide();
    }
    hoverTimer = setTimeout(show, HOVER_DELAY);
  };

  const handleMouseleave = () => {
    // 移出只取消未触发的展开计时，已展开的菜单保持展开，交由点击外部收起
    clearHoverTimer();
  };

  // 菜单里的子弹层（如 DbPopconfirm）被 tippy 挂到 body 上，点击它不算点击外部
  const isInChildPopper = (path: EventTarget[]) =>
    path.some((target) => {
      // _tippy 是 tippy.js 挂在 DOM 元素上的实例引用，属性名由库决定
      // eslint-disable-next-line no-underscore-dangle
      const instance = (target as { _tippy?: Instance } & HTMLElement)._tippy;
      return !!instance && instance.popper === target && !!contentRef.value?.contains(instance.reference);
    });

  const handleDocumentClick = (event: MouseEvent) => {
    const path = event.composedPath();
    if (rootRef.value && path.includes(rootRef.value)) {
      return;
    }
    if (tippyInstance && path.includes(tippyInstance.popper)) {
      return;
    }
    if (isInChildPopper(path)) {
      return;
    }
    hide();
  };

  watch(isPopoverShow, (isShow) => {
    clearHoverTimer();
    if (isShow) {
      isContentMounted.value = true;
      activeHide = hide;
      tippyInstance?.show();
      // 捕获阶段监听，避免内容区内阻止冒泡导致无法判断
      document.addEventListener('click', handleDocumentClick, true);
      emits('show');
      return;
    }
    if (activeHide === hide) {
      activeHide = undefined;
    }
    tippyInstance?.hide();
    document.removeEventListener('click', handleDocumentClick, true);
    emits('hide');
  });

  watch(
    () => props.disabled,
    (disabled) => {
      if (disabled) {
        hide();
      }
    },
  );

  watch(
    () => props.placement,
    (placement) => {
      tippyInstance?.setProps({ placement });
    },
  );

  onMounted(() => {
    if (!referenceRef.value || !contentRef.value) {
      return;
    }
    tippyInstance = tippy(referenceRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: false,
      content: contentRef.value,
      hideOnClick: false,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 6],
      placement: props.placement,
      theme: 'dbm-dropdown',
      trigger: 'manual',
      zIndex: 9999,
    });
    // 内容首次渲染或尺寸变化时重新定位
    resizeObserver = new ResizeObserver(() => {
      tippyInstance?.popperInstance?.update();
    });
    resizeObserver.observe(contentRef.value);
    // 菜单被 tippy 移到 body 下，百分比宽度失去参照，把触发元素宽度同步成 CSS 变量供菜单取最小宽度
    referenceObserver = new ResizeObserver(() => {
      if (!referenceRef.value || !contentRef.value) {
        return;
      }
      contentRef.value.style.setProperty(
        '--dbm-dropdown-reference-width',
        `${referenceRef.value.getBoundingClientRect().width}px`,
      );
      tippyInstance?.popperInstance?.update();
    });
    referenceObserver.observe(referenceRef.value);
  });

  onBeforeUnmount(() => {
    clearHoverTimer();
    document.removeEventListener('click', handleDocumentClick, true);
    if (activeHide === hide) {
      activeHide = undefined;
    }
    resizeObserver?.disconnect();
    resizeObserver = undefined;
    referenceObserver?.disconnect();
    referenceObserver = undefined;
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  });
</script>

<style lang="less">
  .dbm-dropdown {
    display: inline-block;

    .dbm-dropdown-reference {
      position: relative;
      z-index: 1;
    }
  }

  // tippy 弹层容器：去除默认背景与内边距，样式交由内容区自行控制
  .tippy-box[data-theme~='dbm-dropdown'] {
    background-color: transparent;

    .tippy-content {
      padding: 0;
    }
  }

  .dbm-dropdown-content {
    background-color: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 6px rgb(51 60 72 / 10%);
  }
</style>
