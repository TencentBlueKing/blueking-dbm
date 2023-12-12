<template>
  <div class="dbm-router-view">
    <ApplyPermissionPage
      v-if="needApplyPermission"
      :data="permissionResult" />
    <SkeletonLoading
      v-else
      :loading="skeletonLoading"
      :name="skeletonName">
      <RouterView />
    </SkeletonLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    onBeforeUnmount,
    ref,
  } from 'vue';
  import {
    type RouteLocationMatched,
    useRoute,
  } from 'vue-router';

  import ApplyDataModel from '@services/model/iam/apply-data';

  import { useEventBus } from '@hooks';

  import ApplyPermissionPage from '@components/apply-permission/page.vue';
  import SkeletonLoading from '@components/skeleton-loading/Index.vue';

  const eventBus = useEventBus();

  const permissionResult = ref(new ApplyDataModel());
  const needApplyPermission = ref(false);

  const route = useRoute();

  const skeletonName = ref<string>();
  const skeletonLoading = ref(false);

  const currentInstanceTimer = 0;
  const getCurrentPageSkeletonLoading = (currentRoute: RouteLocationMatched) => {
    if (!currentRoute.instances.default) {
      setTimeout(() => {
        getCurrentPageSkeletonLoading(currentRoute);
      }, 100);
      return;
    }
    clearTimeout(currentInstanceTimer);
  };


  watch(route, () => {
    needApplyPermission.value = false;

    clearTimeout(currentInstanceTimer);
    const currentRoute = _.last(route.matched);
    if (currentRoute && currentRoute.meta.skeleton) {
      skeletonName.value = currentRoute.meta.skeleton;
      skeletonLoading.value = true;
      getCurrentPageSkeletonLoading(currentRoute);
    }
  }, {
    immediate: true,
  });

  const handlePermissionPage = (data: any) => {
    needApplyPermission.value = true;
    permissionResult.value = data as ApplyDataModel;
  };

  eventBus.on('permission-page', handlePermissionPage);

  onBeforeUnmount(() => {
    eventBus.off('permission-page', handlePermissionPage);
  });
</script>
<style lang="less">
  .dbm-router-view {
    display: block
  }
</style>
