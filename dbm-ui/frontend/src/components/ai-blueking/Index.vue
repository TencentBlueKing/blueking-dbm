<template>
  <AIBlueking
    v-if="apiUrl"
    ref="aiBluekingRef"
    :enable-popup="false"
    ext-cls="dbm-ai-chat-dialog"
    :hide-nimbus="hideNimbus"
    load-recent-session-on-mount
    :show-history-icon="showHistoryIcon"
    :show-more-icon="showMoreIcon"
    :show-new-chat-icon="showNewChatIcon"
    :url="apiUrl" />
</template>

<script setup lang="ts">
  import AIBlueking from '@blueking/ai-blueking';

  import '@blueking/ai-blueking/dist/vue3/style.css';

  import { useState } from './hooks/useState';

  const { aiBluekingRef, apiUrl, hideNimbus, showHistoryIcon, showMoreIcon, showNewChatIcon } = useState();
</script>
<style lang="postcss">
  .dbm-ai-chat-dialog {
    .shortcuts-bar {
      display: none !important;
    }
  }
</style>
