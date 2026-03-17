<template>
  <div id="dbmAiChatContent">
    <AIBlueking
      v-if="isMounted"
      ref="aiBlueking"
      :draggable="false"
      :hide-nimbus="false"
      :request-options="{
        beforeRequest: (requestData: any) => {
          return {
            ...requestData,
            headers: {
              'X-CSRFToken': CSRFToken,
            },
            data: {
              ...(requestData.data || {}),
              agent_code: agentCode,
            },
            params: {
              ...(requestData.params || {}),
              agent_code: agentCode,
            },
          };
        },
      }"
      teleport-to="#dbmAiChatContent"
      :url="url" />
  </div>
</template>
<script setup lang="ts">
  import Cookie from 'js-cookie';
  import urlJoin from 'url-join';

  import AIBlueking from '@blueking/ai-blueking';

  interface Props {
    agentCode: string;
  }

  defineProps<Props>();

  const CSRFToken = Cookie.get('dbm_csrftoken');

  const isMounted = ref(false);

  const url = urlJoin(window.PROJECT_ENV.VITE_AJAX_URL_PREFIX, '/apis/ai/agent');

  const aiBluekingRef = useTemplateRef<InstanceType<typeof AIBlueking>>('aiBlueking');

  onMounted(() => {
    isMounted.value = true;
    setTimeout(() => {
      aiBluekingRef.value?.handleShow();
    }, 20);
  });
</script>
<style lang="postcss">
  #dbmAiChatContent {
    z-index: 1;
    height: 100%;
    background: #fff;

    .ai-blueking-wrapper {
      position: relative;
      width: 100% !important;
      height: 100%;

      & > div {
        width: unset !important;
        height: unset !important;
      }

      .nimbus-container,
      .nimbus-bkai-wrapper {
        width: unset !important;
        height: unset !important;
      }

      .ai-blueking-container-wrapper {
        height: 100% !important;
        transform: unset !important;

        .header {
          display: none;
        }
      }
    }
  }
</style>
