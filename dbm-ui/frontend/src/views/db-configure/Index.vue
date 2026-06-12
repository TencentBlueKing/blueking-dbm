<template>
  <RouterView />
</template>

<script setup lang="ts">
  import { clearConfigureState } from './utils/configureState';

  onBeforeRouteLeave(() => {
    clearConfigureState();
  });
</script>
