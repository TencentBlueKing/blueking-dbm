<template>
  <div class="db-ai-chat-page">
    <BkResizeLayout
      collapsible
      :initial-divide="300"
      style="height: 100%">
      <template #aside>
        <ChatHistoryList v-model="currentSessionCode" />
      </template>
      <template #main>
        <AiBlueking :session-code="currentSessionCode" />
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts">
  import AiBlueking from './components/ai-blueking.vue';
  import ChatHistoryList from './components/chat-history-list.vue';

  const currentSessionCode = ref<string>('');
</script>
<style lang="postcss">
  .db-ai-chat-page {
    display: block;
    height: calc(100vh - var(--notice-height) - 105px);
  }
</style>
