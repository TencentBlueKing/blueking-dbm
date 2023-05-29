<template>
  <div
    class="block-card"
    :class="{ 'is-toggle': isToggle }">
    <div
      class="card-title"
      @click="handleTogglle">
      <div class="card-toggle-flag">
        <DbIcon type="down-shape" />
      </div>
      <slot name="title" />
    </div>
    <BKCollapseTransition>
      <div
        v-show="isToggle"
        class="card-content">
        <slot />
      </div>
    </BKCollapseTransition>
  </div>
</template>
<script setup lang="ts">
  import BKCollapseTransition from 'bkui-vue/lib/collapse-transition';
  import { ref } from 'vue';

  const isToggle = ref(true);

  const handleTogglle = () => {
    isToggle.value = !isToggle.value;
  };
</script>
<style lang="less" scoped>
  .block-card {
    padding: 16px 24px;
    background-color: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 #1919290d;

    & ~ .block-card {
      margin-top: 16px;
    }

    &.is-toggle {
      .card-toggle-flag {
        transform: rotateZ(0);
      }
    }

    .card-title {
      display: flex;
      font-size: 14px;
      font-weight: 700;
      line-height: 22px;
      color: #313238;
      align-items: center;
      cursor: pointer;
    }

    .card-toggle-flag {
      margin-right: 8px;
      transform: rotateZ(-90deg);
      transition: all 0.15s;
    }

    .card-content {
      margin-top: 16px;
    }
  }
</style>
