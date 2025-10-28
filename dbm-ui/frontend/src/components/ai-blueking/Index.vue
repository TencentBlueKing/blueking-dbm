<template>
  <AIBlueking
    v-if="apiUrl"
    default-minimize
    :url="apiUrl" />
</template>

<script setup lang="ts">
  import AIBlueking from '@blueking/ai-blueking';

  import { useSystemEnviron } from '@stores';

  import '@blueking/ai-blueking/dist/vue3/style.css';

  const systemEnvironStore = useSystemEnviron();

  const { BK_AIDEV_URL: apiUrl } = systemEnvironStore.urls;
</script>
