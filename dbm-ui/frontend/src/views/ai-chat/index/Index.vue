<template>
  <div
    v-bk-loading="{ loading: isAgentPingLoading }"
    class="db-ai-chat-page">
    <BkResizeLayout
      v-if="!isAgentPingLoading && !isAgentPingError"
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
    <BkException
      v-if="isAgentPingError"
      style="margin-top: 100px"
      type="500">
      <template #description>
        <I18nT keypath="蓝鲸 AIDev 服务暂时不可用，请稍后重试 ...">
          <BkButton
            text
            theme="primary"
            @click="handleRetry">
            {{ t('重试') }}
          </BkButton>
        </I18nT>
      </template>
    </BkException>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAgentPing } from '@services/source/ai';

  import AiBlueking from './components/ai-blueking.vue';
  import ChatHistoryList from './components/chat-history-list.vue';

  const { t } = useI18n();

  const isAgentPingError = ref(false);

  const { loading: isAgentPingLoading, runAsync: runAgentPing } = useRequest(getAgentPing, {
    onError: () => {
      isAgentPingError.value = true;
    },
  });

  const currentSessionCode = ref<string>('');

  const handleRetry = () => {
    runAgentPing();
  };
</script>
<style lang="postcss">
  .db-ai-chat-page {
    display: block;
    height: calc(100vh - var(--notice-height) - 105px);
  }
</style>
