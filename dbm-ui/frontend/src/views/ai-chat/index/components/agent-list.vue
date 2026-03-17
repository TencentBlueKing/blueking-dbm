<template>
  <div
    v-bk-loading="{ loading }"
    class="ai-agent-list-box">
    <div class="agent-search-box">
      <BkInput
        v-model="searchKeyword"
        :placeholder="t('搜索智能体...')"
        type="search" />
    </div>
    <ScrollFaker>
      <div class="agent-group-list">
        <div
          v-for="(agents, group) in filteredWorkbench"
          :key="group"
          class="agent-group">
          <div
            class="agent-group-header"
            @click="handleToggleGroup(group as string)">
            <DbIcon
              class="agent-group-arrow"
              :class="{
                'is-collapsed': collapsedGroups[group],
              }"
              type="down-shape" />
            <span class="agent-group-title">{{ group }}</span>
          </div>
          <template v-if="!collapsedGroups[group]">
            <div
              v-for="agent in agents"
              :key="agent.id"
              class="agent-item"
              :class="{ 'is-active': modelValue === agent.id }"
              @click="handleSelect(agent)">
              <div class="agent-item-name">{{ agent.name }}</div>
              <div class="agent-item-desc">{{ agent.description }}</div>
            </div>
          </template>
        </div>
        <BkException
          v-if="isEmptyResult"
          scene="part"
          style="margin-top: 80px"
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
      </div>
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAgentScene } from '@services/source/ai';

  defineOptions({
    name: 'AgentList',
  });

  const modelValue = defineModel<string>();

  type AgentItem = { description: string; id: string; name: string };

  const { t } = useI18n();

  const searchKeyword = ref('');
  const collapsedGroups = ref<Record<string, boolean>>({});

  const { data: agentScene, loading } = useRequest(getAgentScene, {
    onSuccess: (data) => {
      modelValue.value = Object.values(data.workbench)[0][0]?.id || '';
    },
  });

  const filteredWorkbench = computed(() => {
    const workbench = agentScene.value?.workbench;
    if (!workbench) return {};

    const keyword = searchKeyword.value.toLowerCase();
    if (!keyword) return workbench;

    const result: Record<string, AgentItem[]> = {};
    for (const [group, agents] of Object.entries(workbench)) {
      const matched = agents.filter(
        (agent) => agent.name.toLowerCase().includes(keyword) || agent.description.toLowerCase().includes(keyword),
      );
      if (matched.length > 0) {
        result[group] = matched;
      }
    }
    return result;
  });

  const isEmptyResult = computed(() => Object.keys(filteredWorkbench.value).length === 0 && !loading.value);

  const handleToggleGroup = (group: string) => {
    collapsedGroups.value[group] = !collapsedGroups.value[group];
  };

  const handleSelect = (agent: AgentItem) => {
    modelValue.value = agent.id;
  };
  const handleClearSearch = () => {
    searchKeyword.value = '';
  };
</script>
<style lang="postcss">
  .ai-agent-list-box {
    .agent-search-box {
      margin: 12px 16px;
    }

    .agent-group-list {
      padding: 0;
    }

    .agent-group-header {
      display: flex;
      height: 36px;
      padding: 0 16px;
      font-size: 14px;
      font-weight: bold;
      color: #313238;
      cursor: pointer;
      align-items: center;
      gap: 4px;

      &:hover {
        background: #f0f1f5;
        border-radius: 2px;
      }
    }

    .agent-group-arrow {
      font-size: 14px;
      color: #979ba5;
      transition: transform 0.2s;

      &.is-collapsed {
        transform: rotate(-90deg);
      }
    }

    .agent-item {
      padding: 8px 16px 8px 32px;
      cursor: pointer;
      background: #fff;
      border-radius: 2px;
      transition: background 0.2s;

      &:hover {
        background: #f0f1f5;
      }

      &.is-active {
        background: #e1ecff;

        .agent-item-name {
          color: #3a84ff;
        }
      }

      & ~ .agent-item {
        margin-top: 8px;
      }
    }

    .agent-item-name {
      font-size: 13px;
      font-weight: bold;
      line-height: 22px;
      color: #4d4f56;
    }

    .agent-item-desc {
      overflow: hidden;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
