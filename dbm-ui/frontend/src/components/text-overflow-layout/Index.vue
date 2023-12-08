<template>
  <div
    ref="rootRef"
    class="text-overflow-layout">
    <div
      v-if="slots.prepend"
      class="layout-prepend">
      <slot name="prepend" />
    </div>
    <div
      ref="contentRef"
      v-bk-tooltips="{
        content: overflowTips,
        disabled: !overflowTips
      }"
      class="layout-content">
      <div>
        <slot />
      </div>
    </div>
    <div
      v-if="slots.append"
      class="layout-append">
      <slot name="append" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    onBeforeUnmount,
    onMounted,
    ref,
  } from 'vue';

  import { calcTextWidth } from '@utils';

  const slots = defineSlots<Partial<{
    prepend(): any;
    default(): any;
    append(): any;
  }>>();

  const rootRef = ref();
  const contentRef = ref<HTMLElement>();

  const overflowTips = ref('');

  onMounted(() => {
    const resizeObserver = new ResizeObserver(_.throttle(() => {
      const tips = contentRef.value!.innerText;
      const boxWidth = contentRef.value!.getBoundingClientRect().width;
      const textWidth = calcTextWidth(tips, contentRef.value);
      overflowTips.value = boxWidth < textWidth ? tips : '';
    }, 100));
    resizeObserver.observe(rootRef.value);

    onBeforeUnmount(() => {
      resizeObserver.unobserve(rootRef.value);
      resizeObserver.disconnect();
    });
  });
</script>
<style lang="less">
  .text-overflow-layout {
    display: flex;
    overflow: hidden;
    align-items: center;

    .layout-prepend,
    .layout-content,
    .layout-append {
      display: flex;
      align-items: center;
    }

    .layout-content{
      overflow: hidden;
      flex: 0 1 auto;

      & * {
        display: block;
        width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
</style>
