<template>
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
          @update-success="handleUpdateDetailSuccess" />
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

  const isSpecial = computed(() => activePanel.value === 'special_demand');

  const panels = [
    { label: t('业务风险'), name: 'biz_risk' },
    { label: t('业务特殊要求'), name: 'special_demand' },
  ];

  watch(
    activePanel,
    () => {
      nextTick(() => {
        router.push({
          query: {
            status: 'backlog',
            tab: activePanel.value,
          },
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

  const handleUpdateDetailSuccess = () => {
    riskListRef.value!.refresh();
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
      margin-top: -2px;
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
</style>
