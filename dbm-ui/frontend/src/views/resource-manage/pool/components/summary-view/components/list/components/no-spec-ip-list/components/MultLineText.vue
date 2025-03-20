<template>
  <div class="ip-mult-line-text">
    <div
      ref="rootRef"
      class="ip-mult-line-text-wrapper">
      <slot />
      <div
        ref="placeholderRef"
        class="placeholder">
        <slot />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { Instance, SingleTarget } from 'tippy.js';

  import { dbTippy } from '@common/tippy';

  let tippyInst: Instance;

  const rootRef = ref<HTMLElement>();
  const placeholderRef = ref<HTMLElement>();

  const calcShowExpand = () => {
    nextTick(() => {
      const { height: placeholderHeight } = placeholderRef.value!.getBoundingClientRect();

      if (rootHeight < placeholderHeight) {
        createTippyInst();
      }
    });
  };
  let rootHeight = 0;

  const createTippyInst = () => {
    const { width } = rootRef.value!.getBoundingClientRect();
    tippyInst = dbTippy(rootRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: true,
      content: placeholderRef.value,
      maxWidth: width,
      zIndex: 999999,
    });
  };

  const destroyTippyInst = () => {
    if (tippyInst) {
      tippyInst.hide();
      tippyInst.unmount();
      tippyInst.destroy();
    }
  };

  onMounted(() => {
    rootHeight = rootRef.value!.getBoundingClientRect().height;
    calcShowExpand();
  });

  onBeforeUpdate(() => {
    destroyTippyInst();
    calcShowExpand();
  });
</script>
<style lang="less">
  .ip-mult-line-text {
    .ip-mult-line-text-wrapper {
      position: relative;
      display: -webkit-box;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: normal;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 3;
    }

    .placeholder {
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      z-index: -1;
      word-break: normal;
    }
  }
</style>
