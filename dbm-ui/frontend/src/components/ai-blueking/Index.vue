<template>
  <AIBlueking
    v-if="apiUrl"
    ref="aiBluekingRef"
    :enable-popup="false"
    load-recent-session-on-mount
    :url="apiUrl" />
</template>

<script setup lang="ts">
  import AIBlueking from '@blueking/ai-blueking';

  import '@blueking/ai-blueking/dist/vue3/style.css';

  import { useState } from './hooks/useState';

  const { aiBluekingRef, apiUrl } = useState();
</script>
