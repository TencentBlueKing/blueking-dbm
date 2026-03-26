<template>
  <BkLoading :loading="(isSwitchingSessionLoading || isSessionListLoading) && !isCreatingSession">
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
        :request-options="{
          beforeRequest: (requestData: any) => {
            return {
              ...requestData,
              headers: {
                'X-CSRFToken': CSRFToken,
              },
              data: {
                ...(requestData.data || {}),
                agent_code: agentInfo.id,
              },
              params: {
                ...(requestData.params || {}),
                agent_code: agentInfo.id,
              },
            };
          },
        }"
        teleport-to="#dbmAiChatContent"
        :url="url" />
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import Cookie from 'js-cookie';
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

  interface SessionItem {
    created_at: string;
    created_by: string;
    model: string;
    protocol_version: string;
    role_info: {
      generate_type: string;
      role_content: { extra: null | string; id: null | number; role: string }[];
      role_id: number;
      role_name: string;
      role_variable: unknown[];
      status: string;
    };
    session_code: string;
    session_content_count: number;
    session_name: string;
    session_property: {
      flow_info: null | string;
      is_auto_clac_prompt: boolean;
      is_auto_clear: boolean;
      test_code: null | string;
    };
    sessionsession_codeCode: string;
    status: null | string;
    updated_at: string;
    updated_by: string;
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

  const sessionList = ref<
    {
      sessionCode: string;
      sessionName: string;
      updatedAt: string;
    }[]
  >([]);

  const url = urlJoin(window.PROJECT_ENV.VITE_AJAX_URL_PREFIX, '/apis/ai/agent');

  const aiBluekingRef = useTemplateRef<InstanceType<typeof AIBlueking>>('aiBlueking');
  const isSwitchingSessionLoading = ref(false);

  const agentPrefix = computed(() => `[${props.agentInfo.id}]`);

  const switchToSession = (sessionCode: string) => {
    isSwitchingSessionLoading.value = true;
    aiBluekingRef.value?.switchToSession(sessionCode).finally(() => {
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

  const fetchSessionList = async () => {
    isSessionListLoading.value = true;
    try {
      const dataList: {
        sessionCode: string;
        sessionName: string;
        updatedAt: string;
      }[] = await aiBluekingRef.value?.getSessionList();

      sessionList.value = dataList.filter(
        (item) => item.sessionCode.startsWith(agentPrefix.value) && item.sessionName !== 'temporary_session',
      );
    } finally {
      setTimeout(() => {
        isSessionListLoading.value = false;
      }, 300);
    }
  };

  const handleNewChat = () => {
    isCreatingSession.value = true;
    aiBluekingRef.value
      ?.addNewSession(`${agentPrefix.value}${uuid()}`)
      .then((data: SessionItem) => {
        fetchSessionList();
        switchToSession(data.session_code);
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
    isSwitchingSessionLoading.value = true;
    setTimeout(async () => {
      await aiBluekingRef.value?.handleShow();
      await fetchSessionList();
      if (sessionList.value.length > 0) {
        switchToSession(sessionList.value[0].sessionCode);
      } else {
        handleNewChat();
      }
    });
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

    .ai-blueking-wrapper {
      position: relative;
      z-index: 0;
      width: 100% !important;
      height: calc(100vh - 104px - var(--notice-height));

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
