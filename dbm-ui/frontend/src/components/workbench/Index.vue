<template>
  <div
    class="workbench"
    :class="{
      'active': isActive
    }"
    @click="handleClick">
    <DbIcon type="pc" />
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  const route = useRoute();
  const router = useRouter();

  const isActive = computed(() => ['SelfServiceMyTickets', 'MyTodos'].includes(route.name as string));

  const handleClick = () => {
    if (route.name === 'SelfServiceMyTickets') {
      return;
    }
    router.push({
      name: 'SelfServiceMyTickets',
    });
  };
</script>
<style lang="less" scoped>
  .workbench {
    position: relative;
    display: inline-flex;
    width: 32px;
    height: 32px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    border-radius: 50%;
    transition: background .15s;
    align-items: center;
    justify-content: center;

    &:hover,
    &.active {
      color: @primary-color;
      background-color: #f0f1f5;
    }
  }
</style>
