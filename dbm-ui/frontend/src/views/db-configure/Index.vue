<template>
  <RouterView />
</template>

<script setup lang="ts">
  import { clearConfigureState } from './utils/configureState';

  const router = useRouter();

  /**
   * 组件离开钩子早于全局守卫的离开确认，用户可能取消离开；等导航真正完成再清，页面留下时保留选中状态
   */
  onBeforeRouteLeave(() => {
    const removeAfterEach = router.afterEach((to, from, failure) => {
      removeAfterEach();
      if (!failure) {
        clearConfigureState();
      }
    });
  });
</script>
