<template>
  <Teleport
    v-if="isTodoPage"
    to="#dbContentTitleAppend">
    <div class="risk-memo-todo-page-title-icon">
      <DbIcon
        v-bk-tooltips="titleTooltip"
        type="attention" />
    </div>
  </Teleport>
  <Teleport
    v-if="isTodoPage"
    to="#dbContentHeaderAppend">
    <div class="risk-memo-todo-page-head-controls-main">
      <div
        class="tab-item tab-item-todo"
        :class="{ 'tab-item-active': isTodoTab }"
        @click="() => handleClickTab('todo')">
        <DbIcon
          class="control-icon"
          type="wodedaiban" />
        <span>{{ t('待我处理') }}</span>
      </div>
      <div
        class="tab-item tab-item-assist"
        :class="{ 'tab-item-active': !isTodoTab }"
        @click="() => handleClickTab('assist')">
        <DbIcon
          class="control-icon"
          type="yonghu-2" />
        <span>{{ t('待我协助') }}</span>
      </div>
    </div>
  </Teleport>
  <div
    ref="riskMemoMainPageRef"
    class="risk-memo-main-page">
    <BkTab
      v-model:active="activePanel"
      class="header-tab"
      type="unborder-card">
      <BkTabPanel
        v-for="panel in panels"
        :key="panel.name"
        :label="panel.label"
        :name="panel.name">
      </BkTabPanel>
    </BkTab>
    <BkResizeLayout
      class="content-main"
      collapsible
      :initial-divide="460"
      :max="resizeMax"
      :min="460"
      placement="left">
      <template #aside>
        <RiskList
          ref="riskListRef"
          :is-special="isSpecial"
          @choose-item="handleChooseRiskItem" />
      </template>
      <template #main>
        <RiskDetail
          :is-special="isSpecial"
          :risk-id="currentRiskId"
          @update-success="handleRefreshList" />
      </template>
    </BkResizeLayout>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import RiskDetail from './components/detail/Index.vue';
  import RiskList from './components/list/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const riskMemoMainPageRef = ref<HTMLDivElement>();
  const riskListRef = ref<InstanceType<typeof RiskList>>();
  const activePanel = ref((route.query.tab as string) || 'biz_risk');
  const currentRiskId = ref(0);
  const resizeMax = ref(1000);
  const currentActiveTab = ref('');
  const titleTooltip = `${t('待我处理')}：${t('展示我作为主DBA 的业务，进行中的风险和生效中的要求')}\n${t('待我协助')}：${t('展示我作为备 DBA、二线 DBA 的业务，进行中的风险和生效中的要求')}`;

  const isSpecial = computed(() => activePanel.value === 'special_demand');
  const isTodoPage = computed(() => route.name === 'RiskMemoTodos');
  const isTodoTab = computed(() => currentActiveTab.value === 'todo');

  const panels = [
    { label: t('业务风险'), name: 'biz_risk' },
    { label: t('业务特殊要求'), name: 'special_demand' },
  ];

  watch(
    isTodoPage,
    () => {
      if (isTodoPage.value) {
        const isAssistParam = route.query.is_assist;
        if (isAssistParam) {
          currentActiveTab.value = isAssistParam === 'true' ? 'assist' : 'todo';
        } else {
          currentActiveTab.value = 'todo';
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [activePanel.value, currentActiveTab.value],
    () => {
      const query = {
        status: 'backlog',
        tab: activePanel.value,
      };
      if (currentActiveTab.value) {
        Object.assign(query, {
          is_assist: currentActiveTab.value === 'assist',
        });
      }
      nextTick(() => {
        router.push({
          query,
        });
      });
    },
    {
      immediate: true,
    },
  );

  const handleChooseRiskItem = (id: number) => {
    currentRiskId.value = id;
  };

  const handleRefreshList = () => {
    riskListRef.value!.refresh();
  };

  const handleClickTab = (tab: string) => {
    currentActiveTab.value = tab;
    setTimeout(() => {
      handleRefreshList();
    });
  };

  onMounted(() => {
    resizeMax.value = riskMemoMainPageRef.value!.clientWidth / 2;
  });
</script>
<style lang="less">
  .risk-memo-main-page {
    display: flex;
    flex-direction: column;
    height: 100%;

    .header-tab {
      position: relative;
      z-index: 999;
      padding-left: 24px;
      margin-top: 2px;
      background: #fff;
      box-shadow: 0 3px 4px 0 #0000000a;

      .bk-tab-header {
        border-bottom: none;
      }

      .bk-tab-content {
        display: none;
      }
    }

    .content-main {
      display: flex;
      overflow: hidden;
      flex: 1;
      border: none;

      .bk-resize-layout-aside {
        border-color: transparent;

        &:hover {
          border-color: #3a84ff;
        }
      }
    }
  }

  .risk-memo-todo-page-title-icon {
    display: flex;
    margin-right: 12px;
    margin-left: 6px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    align-items: center;
  }

  .risk-memo-todo-page-head-controls-main {
    position: relative;
    display: flex;
    padding-left: 12px;

    &::before {
      position: absolute;
      top: 9px;
      left: 0;
      width: 1px;
      height: 14px;
      background: #c4c6cc;
      content: '';
    }

    .tab-item {
      display: flex;
      height: 32px;
      padding: 0 10px 0 8px;
      font-size: 14px;
      color: #4d4f56;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;

      &.tab-item-active {
        color: #3a84ff;
        background: #f0f5ff;
      }

      &.tab-item-todo {
        border-radius: 2px 0 0 2px;
      }

      &.tab-item-assist {
        position: relative;
        border-radius: 0 2px 2px 0;

        &::before {
          position: absolute;
          top: 9px;
          left: 0;
          width: 1px;
          height: 14px;
          background: #c4c6cc;
          content: '';
        }
      }

      .control-icon {
        margin-right: 5px;
        font-size: 14px;
      }
    }
  }
</style>
