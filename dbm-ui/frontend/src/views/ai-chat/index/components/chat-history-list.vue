<template>
  <div
    v-bk-loading="{ loading: isSessionListLoading }"
    class="ai-chat-history-box">
    <div class="session-search-box">
      <BkInput
        class="session-search-input"
        :model-value="searchKeyword"
        :placeholder="t('搜索会话')"
        type="search"
        @input="handleSearch" />
    </div>
    <div class="session-create-btn">
      <BkButton
        :loading="isCreatSubmitting"
        style="width: 100%"
        @click="handleCreateSession">
        <DbIcon type="add" />
        {{ t('新建会话') }}
      </BkButton>
    </div>
    <div
      class="ai-chat-history-wrapper"
      :class="{ 'is-selected': selectedSessionCount > 0 }">
      <ScrollFaker>
        <div class="ai-chat-history-list">
          <ChatSession
            v-for="item in sessionList"
            :key="item.sessionCode"
            v-model="modelValue"
            :data="item"
            :selected="Boolean(sessionSelectMap[item.sessionCode])"
            @select="() => handleSelect(item.sessionCode)"
            @success="fetchSessionList" />
        </div>
        <BkException
          v-if="sessionList.length === 0"
          scene="part"
          style="margin-top: 100px"
          type="search-empty">
          <template #description>
            {{ t('搜索为空') }}，
            <BkButton
              text
              theme="primary"
              @click="handleClearSearch">
              {{ t('清空搜索条件') }}
            </BkButton>
          </template>
        </BkException>
      </ScrollFaker>
    </div>
    <div
      v-if="selectedSessionCount > 0"
      class="session-list-action">
      <BkCheckbox
        v-bind="sessionListSelectInfo"
        :false-label="false"
        :true-label="trueLabel"
        @change="handleSelectAll">
        {{ t('全选') }}
      </BkCheckbox>
      <DbPopconfirm
        :confirm-handler="handleBatchDeleteSession"
        :content="t('删除对话将删除该会话的所有聊天记录，请谨慎操作。')"
        style="margin-left: auto"
        :title="
          t('确认删除 n 个对话？', {
            n: selectedSessionCount,
          })
        ">
        <BkButton
          :loading="isBatchDeleting"
          theme="primary">
          {{ t('批量删除') }}
          <span class="ml-4">({{ selectedSessionCount }})</span>
        </BkButton>
      </DbPopconfirm>
      <BkButton
        class="ml-8"
        @click="handleCancelSelect">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import AIBlueking from '@blueking/ai-blueking';

  import { batchDeleteSession } from '@services/source/ai';

  import ChatSession from './chat-session.vue';
  import { uuid } from './utils';

  type ISession = ServiceReturnType<ComponentExposed<typeof AIBlueking>['getSessionList']>[number];

  interface Props {
    addNewSession: ComponentExposed<typeof AIBlueking>['addNewSession'];
    getSessionList: ComponentExposed<typeof AIBlueking>['getSessionList'];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>('modelValue');

  const { t } = useI18n();

  const trueLabel = true;

  const isSessionListLoading = ref(false);
  const isCreatSubmitting = ref(false);
  const wholeSessionList = ref<ISession[]>([]);
  const sessionList = ref<ISession[]>([]);
  const sessionSelectMap = ref<Record<string, boolean>>({});
  const searchKeyword = ref<string>('');

  const sessionListSelectInfo = computed(() => {
    if (sessionList.value.length === 0) {
      return {
        indeterminate: false,
        modelValue: false,
      };
    }
    let indeterminate = false;
    let modelValue = true;
    for (const item of sessionList.value) {
      if (sessionSelectMap.value[item.sessionCode]) {
        indeterminate = true;
      } else {
        modelValue = false;
      }
    }
    return {
      indeterminate: modelValue ? false : indeterminate,
      modelValue,
    };
  });

  const selectedSessionCount = computed(() => Object.keys(sessionSelectMap.value).length);

  const { loading: isBatchDeleting, runAsync: runBatchDeleteSession } = useRequest(batchDeleteSession, {
    manual: true,
    onSuccess: () => {
      fetchSessionList();
    },
  });

  const fetchSessionList = () => {
    isSessionListLoading.value = true;
    props
      .getSessionList()
      .then((data) => {
        wholeSessionList.value = _.orderBy(
          _.filter(data, (item) => item.sessionName !== 'temporary_session'),
          ['updated_at'],
        );

        handleSearch(searchKeyword.value);

        nextTick(() => {
          if (
            (!modelValue.value ||
              (modelValue.value && !wholeSessionList.value.some((item) => item.sessionCode === modelValue.value))) &&
            wholeSessionList.value.length > 0
          ) {
            modelValue.value = wholeSessionList.value[0].sessionCode;
          }
        });
      })
      .finally(() => {
        isSessionListLoading.value = false;
      });
  };

  const handleSearch = _.throttle((value: string) => {
    searchKeyword.value = value;
    if (!value) {
      sessionList.value = [...wholeSessionList.value];
      return;
    }
    sessionList.value = _.filter(wholeSessionList.value, (item) =>
      item.sessionName.toLowerCase().includes(value.toLowerCase()),
    );
  }, 300);

  const handleCreateSession = () => {
    isCreatSubmitting.value = true;
    props
      .addNewSession(uuid())
      .then((data) => {
        modelValue.value = data.sessionCode;
        fetchSessionList();
      })
      .finally(() => {
        isCreatSubmitting.value = false;
      });
  };

  const handleSelect = (sessionCode: string) => {
    const selectMap = { ...sessionSelectMap.value };
    if (selectMap[sessionCode]) {
      delete selectMap[sessionCode];
    } else {
      selectMap[sessionCode] = true;
    }
    sessionSelectMap.value = selectMap;
  };

  const handleSelectAll = () => {
    if (!sessionListSelectInfo.value.modelValue) {
      const selectMap: Record<string, boolean> = {};
      for (const item of sessionList.value) {
        selectMap[item.sessionCode] = true;
      }
      sessionSelectMap.value = selectMap;
    } else {
      sessionSelectMap.value = {};
    }
  };

  const handleCancelSelect = () => {
    sessionSelectMap.value = {};
  };

  const handleBatchDeleteSession = () => {
    return runBatchDeleteSession({
      session_codes: Object.keys(sessionSelectMap.value),
    });
  };

  const handleClearSearch = () => {
    searchKeyword.value = '';
    handleSearch(searchKeyword.value);
  };

  onMounted(() => {
    setTimeout(() => {
      fetchSessionList();
    });
  });
</script>
<style lang="postcss">
  .ai-chat-history-box {
    height: 100%;
    overflow: hidden;

    .session-search-box {
      margin: 12px 16px;
    }

    .session-create-btn {
      margin: 12px 16px;
    }

    .ai-chat-history-wrapper {
      height: calc(100% - 116px);

      &.is-selected {
        height: calc(100% - 168px);
      }
    }

    .ai-chat-history-list {
      padding: 0 16px;
    }

    .session-list-action {
      position: absolute;
      right: 0;
      bottom: 0;
      left: 0;
      display: flex;
      height: 52px;
      padding: 0 16px;
      background: #fafbfd;
      border-top: 1px solid #dcdee5;
      align-items: center;
    }
  }
</style>
