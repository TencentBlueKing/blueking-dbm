<template>
  <div class="permission-mult-line-text">
    <div
      ref="rootRef"
      class="permission-mult-line-text-wrapper"
      :style="styles">
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

  interface Props {
    line: number;
  }

  const props = defineProps<Props>();

  let tippyInst: Instance;

  const rootRef = ref<HTMLElement>();
  const placeholderRef = ref<HTMLElement>();
  const isMore = ref(false);

  const styles = computed(() => ({
    '-webkit-line-clamp': isMore.value ? 'initial' : props.line,
  }));

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
      content: placeholderRef.value,
      appendTo: () => document.body,
      maxWidth: width,
      arrow: true,
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
  .permission-mult-line-text {
    .permission-mult-line-text-wrapper {
      position: relative;
      display: -webkit-box;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: normal;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: v-bind('line');
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
