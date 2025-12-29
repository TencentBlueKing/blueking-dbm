<template>
  <AIBlueking
    v-if="isShowAiBlueking"
    ref="aiBluekingRef"
    :enable-popup="false"
    ext-cls="dbm-ai-chat-dialog"
    :hide-nimbus="hideNimbus"
    load-recent-session-on-mount
    nimbus-size="large"
    :show-history-icon="showHistoryIcon"
    :show-more-icon="showMoreIcon"
    :show-new-chat-icon="showNewChatIcon"
    :url="apiUrl" />
</template>

<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import AIBlueking from '@blueking/ai-blueking';

  import { useSystemEnviron } from '@stores';

  import '@blueking/ai-blueking/dist/vue3/style.css';

  import { useState } from './hooks/useState';

  const route = useRoute();

  const systemEnvironStore = useSystemEnviron();

  const { ENABLE_DBM_AI } = systemEnvironStore.urls;

  const { aiBluekingRef, apiUrl, hideNimbus, showHistoryIcon, showMoreIcon, showNewChatIcon } = useState();

  const isShowAiBlueking = computed(() => route.meta.aiBlueking !== false && apiUrl.value && ENABLE_DBM_AI);
</script>
<style lang="postcss">
  .dbm-ai-chat-dialog {
    .shortcuts-bar {
      display: none !important;
    }
  }
</style>
