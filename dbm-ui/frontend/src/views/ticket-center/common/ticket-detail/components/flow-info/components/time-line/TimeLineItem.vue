<template>
  <div class="db-time-line-item">
    <div class="db-time-line-icon">
      <slot name="icon">
        <div class="db-time-line-dot" />
      </slot>
    </div>
    <div class="db-time-line-title">
      <slot name="title" />
    </div>
    <div class="db-time-line-content">
      <slot name="content" />
    </div>
    <div
      v-if="slots.desc"
      class="db-time-line-desc">
      <slot name="desc" />
    </div>
    <div
      v-if="slots.action"
      class="db-time-line-action">
      <slot name="action" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';

  interface Slot {
    icon?: () => VNode | VNode[];
    title: () => VNode | VNode[];
    content: () => VNode | VNode[];
    desc?: () => VNode | VNode[];
    action?: () => VNode | VNode[];
  }

  const slots = defineSlots<Slot>();
</script>
<style lang="less">
  .db-time-line-item {
    position: relative;
    padding-bottom: 20px;
    padding-left: 24px;
    font-size: 12px;
    line-height: 19px;
    color: #63656e;

    &:last-child {
      padding-bottom: 0;

      &::before {
        content: none;
      }
    }

    &::before {
      position: absolute;
      top: 8px;
      left: 7px;
      width: 1px;
      height: 100%;
      background: #d8d8d8;
      content: '';
    }
  }

  .db-time-line-icon {
    position: absolute;
    top: 4px;
    left: 0;
    display: flex;
    width: 15px;
    height: 15px;
    line-height: 1;
    background: #fff;
    align-items: center;
    justify-content: center;
  }

  .db-time-line-dot {
    width: 10px;
    height: 10px;
    background: #fff;
    border: 2px solid #d8d8d8;
    border-radius: 50%;
  }

  .db-time-line-title {
    font-weight: bold;
    color: #313238;
  }

  .db-time-line-content {
    margin-top: 10px;
  }

  .db-time-line-desc {
    margin-top: 10px;
    font-size: 12px;
    line-height: 16px;
    color: #979ba5;
  }

  .db-time-line-action {
    margin-top: 10px;
  }
</style>
