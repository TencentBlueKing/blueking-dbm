<template>
  <div class="router-back">
    <DbIcon
      v-if="showRouterBackBtn"
      class="route-btn"
      type="arrow-left"
      @click="handleRouterBack" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    ref,
    watch,
  } from 'vue';
  import {
    useRoute,
  } from 'vue-router';

  const route = useRoute();

  const showRouterBackBtn = ref(false);
  let routerBack = () => {};

  let timer = 0;

  watch(route, () => {
    clearTimeout(timer);

    showRouterBackBtn.value = false;
    const last = _.last(route.matched);
    timer = setTimeout(() => {
      if (last && last.instances.default) {
        const routerBackFn = (last.instances.default as {routerBack?: () => void}).routerBack;
        if (_.isFunction(routerBackFn)) {
          showRouterBackBtn.value = true;
          routerBack = routerBackFn;
        }
      }
    }, 100);
  });
  const handleRouterBack = () => {
    routerBack();
  };
</script>
<style lang="less">
  .router-back {
    display: inline-flex;
    padding-right: 10px;
    margin-top: 2px;
    font-size: 20px;
    align-items: center;

    .route-btn{
      padding-left: 8px;
      color: #3A84FF;
      cursor: pointer;
    }
  }
</style>
