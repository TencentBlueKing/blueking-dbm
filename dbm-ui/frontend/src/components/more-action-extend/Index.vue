<template>
  <div
    ref="rootRef"
    class="more-action-extend"
    :class="{
      active: isPopoverShow
    }"
    v-bind="attrs"
    @click.stop="handleClick">
    <DbIcon type="more" />
  </div>
  <div
    ref="popRef"
    class="more-action-extend-popover"
    @click="handleHide">
    <template v-if="isPopoverShow">
      <slot />
    </template>
  </div>
</template>
<script lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    onBeforeUnmount,
    onMounted,
    ref,
    useAttrs,
  } from 'vue';

  let activeTippyIns:Instance;
</script>
<script setup lang="ts">
  const rootRef = ref();
  const popRef = ref();

  let tippyIns:Instance | undefined;

  const attrs = useAttrs();

  const isPopoverShow = ref(false);

  const handleClick = () => {
    if (!tippyIns) {
      return;
    }
    if (activeTippyIns && activeTippyIns !== tippyIns) {
      activeTippyIns.hide();
    }
    tippyIns.show();
    activeTippyIns = tippyIns;
  };

  const handleHide = () => {
    activeTippyIns.hide();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom',
      appendTo: () => document.body,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: false,
      offset: [0, 8],
      zIndex: 999999,
      hideOnClick: true,
      onShow() {
        isPopoverShow.value = true;
      },
      onHidden() {
        isPopoverShow.value = false;
      },
    });
  });
  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less">
  .more-action-extend{
    display: inline-flex;
    width: 20px;
    height: 20px;
    font-size: 14px;
    color: #3A84FF;
    cursor: pointer;
    border-radius: 50%;
    justify-content: center;
    align-items: center;

    &:hover,
    &.active{
      background: #dcdee5;
    }
  }

  .more-action-extend-popover {
    display: flex;
    padding: 4px 0;
    margin: -5px -9px;
    font-size: 12px;
    color: #63656E;
    flex-direction: column;

    & > *{
      display: flex;
      height: 32px;
      justify-content: center;
      align-items: center;
      padding: 0 22px 0 12px;
      cursor: pointer;

      &:hover{
        background-color: #F5F7FA;
      }
    }
  }
</style>
