<template>
  <div id="dbmAiChatContent">
    <AIBlueking
      v-if="isMounted"
      ref="aiBlueking"
      :draggable="false"
      :hide-nimbus="false"
      teleport-to="#dbmAiChatContent"
      :url="url" />
  </div>
</template>
<script setup lang="ts">
  import urlJoin from 'url-join';
  import { type ComponentExposed } from 'vue-component-type-helpers';

  import AIBlueking from '@blueking/ai-blueking';

  interface Props {
    sessionCode?: string;
  }

  interface Exposes {
    addNewSession: ComponentExposed<typeof AIBlueking>['addNewSession'];
    getSessionList: ComponentExposed<typeof AIBlueking>['getSessionList'];
  }

  const props = defineProps<Props>();

  const isMounted = ref(false);

  const url = urlJoin(window.PROJECT_ENV.VITE_AJAX_URL_PREFIX, '/apis/ai/agent');

  const aiBluekingRef = useTemplateRef<InstanceType<typeof AIBlueking>>('aiBlueking');

  watch(
    () => props.sessionCode,
    () => {
      if (props.sessionCode) {
        aiBluekingRef.value?.switchToSession(props.sessionCode);
      }
    },
  );

  onMounted(() => {
    isMounted.value = true;
    nextTick(() => {
      aiBluekingRef.value?.handleShow();
    });
  });

  defineExpose<Exposes>({
    addNewSession: (sessionCode?: string) => {
      return aiBluekingRef.value!.addNewSession(sessionCode);
    },
    getSessionList: () => {
      return aiBluekingRef.value!.getSessionList();
    },
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
