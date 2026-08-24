<template>
  <div id="dbmAiChatContent">
    <div class="content-header">
      <div style="font-size: 16px; color: #313238">{{ agentInfo.name }}</div>
      <div class="agent-group-tag">
        {{ agentInfo.group }}
      </div>
      <div class="action-box">
        <BkButton
          :loading="isCreatingSession"
          theme="primary"
          @click="handleNewChat">
          <DbIcon
            class="mr-4"
            type="add" />
          {{ t('新建会话') }}
        </BkButton>
        <ChatHistorySelect
          :active-session-code="activeSessionCode"
          :is-loading="isSessionListLoading"
          :session-list="sessionList"
          @select="handleSelectSession" />
      </div>
    </div>
    <AIBlueking
      v-if="isMounted"
      ref="aiBlueking"
      :draggable="false"
      :hide-nimbus="false"
      :request-options="requestOptions"
      teleport-to="#dbmAiChatContent"
      :url="url" />
  </div>
</template>
<script setup lang="ts">
  import Cookie from 'js-cookie';
  import _ from 'lodash';
  import urlJoin from 'url-join';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import AIBlueking from '@blueking/ai-blueking';

  import { getAgentScene } from '@services/source/ai';

  import ChatHistorySelect from './chat-history-select.vue';
  import { uuid } from './utils';

  interface Props {
    agentInfo: { group: string } & ServiceReturnType<typeof getAgentScene>['workbench'][string][number];
  }

  const props = defineProps<Props>();

  const CSRFToken = Cookie.get('dbm_csrftoken');
  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const isMounted = ref(false);
  const isCreatingSession = ref(false);
  const isSessionListLoading = ref(false);
  const activeSessionCode = ref('');

  const url = urlJoin(window.BK_AJAX_URL, '/apis/ai/agent');

  const aiBluekingRef = useTemplateRef<InstanceType<typeof AIBlueking>>('aiBlueking');
  const isSwitchingSessionLoading = ref(false);

  const agentPrefix = computed(() => `[${props.agentInfo.id}]`);
  const sessionList = computed(() => {
    const list = _.filter(
      aiBluekingRef.value?.getChatHelper()?.session.list.value || [],
      (item) => item.sessionCode.startsWith(agentPrefix.value) && item.sessionName !== 'temporary_session',
    );
    return list;
  });

  const requestOptions = computed(() => {
    return {
      data: {
        agent_code: props.agentInfo.id,
      },
      headers: {
        'X-CSRFToken': CSRFToken,
      },
      params: {
        agent_code: props.agentInfo.id,
      },
    };
  });

  const switchToSession = (sessionCode: string) => {
    isSwitchingSessionLoading.value = true;
    const chatHelper = aiBluekingRef.value!.getChatHelper()!;
    chatHelper.session.chooseSession(sessionCode).finally(() => {
      activeSessionCode.value = sessionCode;
      router.replace({
        name: route.name!,
        params: {
          agentId: props.agentInfo.id,
        },
      });
      setTimeout(() => {
        isSwitchingSessionLoading.value = false;
      }, 300);
    });
  };

  let isInit = false;
  watch(
    () => props.agentInfo,
    () => {
      if (!props.agentInfo) {
        return;
      }
      isSwitchingSessionLoading.value = true;
      setTimeout(async () => {
        if (!isInit) {
          // 只需要 show 一次
          await aiBluekingRef.value?.show();
        }
        isInit = true;
        // show 后，需要等待一下，才能获取到 sessionList
        nextTick(() => {
          aiBluekingRef.value?.updateAgentInfo();
          if (sessionList.value.length > 0) {
            switchToSession(sessionList.value[0].sessionCode);
          } else {
            handleNewChat();
          }
        });
      }, 300);
    },
    {
      immediate: true,
    },
  );

  const handleNewChat = () => {
    isCreatingSession.value = true;
    const chatHelper = aiBluekingRef.value!.getChatHelper()!;
    chatHelper.session
      .createSession({
        sessionCode: `${agentPrefix.value}${uuid()}`,
        sessionName: '新会话',
        sessionProperty: {
          labels: [props.agentInfo.id],
        },
      })
      .then(() => {
        switchToSession(chatHelper.session.current.value?.sessionCode || '');
      })
      .finally(() => {
        isCreatingSession.value = false;
      });
  };

  const handleSelectSession = (sessionCode: string) => {
    switchToSession(sessionCode);
  };

  onMounted(() => {
    isMounted.value = true;
  });
</script>
<style lang="postcss">
  #dbmAiChatContent {
    z-index: 1;
    height: 100%;
    background: #fff;

    .content-header {
      position: relative;
      z-index: 1;
      display: flex;
      height: 52px;
      padding: 0 14px;
      background: #fff;
      box-shadow: 0 3px 4px 0 #0000000a;
      align-items: center;
    }

    .agent-group-tag {
      padding: 0 4px;
      margin-left: 8px;
      font-size: 12px;
      line-height: 20px;
      color: #fff;
      background-color: #3a84ff;
      border-radius: 2px;
    }

    .action-box {
      margin-left: auto;
    }

    .ai-blueking-v2 {
      position: relative;
      z-index: 0;
      width: 100% !important;
      height: calc(100vh - 104px - var(--notice-height));

      .draggable-container-wrapper {
        width: 100% !important;
        height: 100% !important;
        transform: unset !important;
      }

      .ai-blueking-panel {
        border-radius: 0;
      }

      .ai-header {
        display: none !important;
      }
    }
  }
</style>
