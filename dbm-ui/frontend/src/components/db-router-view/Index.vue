<template>
  <div class="dbm-router-view">
    <ApplyPermissionPage
      v-if="needApplyPermission"
      :data="permissionResult" />
    <RouterView v-else />
  </div>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, ref } from 'vue';
  import { useRoute } from 'vue-router';

  import ApplyDataModel from '@services/model/iam/apply-data';

  import { useEventBus } from '@hooks';

  import ApplyPermissionPage from '@components/apply-permission/page.vue';
  // import SkeletonLoading from '@components/skeleton-loading/Index.vue';

  const eventBus = useEventBus();

  const permissionResult = ref(new ApplyDataModel());
  const needApplyPermission = ref(false);

  const route = useRoute();

  const skeletonName = ref<string>();
  const skeletonLoading = ref(false);

  watchEffect(() => {
    skeletonName.value = route.meta.skeleton;

    if (skeletonName.value) {
      skeletonLoading.value = true;
      return;
    }
  });

  watch(
    route,
    () => {
      needApplyPermission.value = false;
    },
    {
      immediate: true,
    },
  );

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
    display: block;
  }
</style>
