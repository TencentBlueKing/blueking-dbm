<template>
  <div class="inspection-todo-page">
    <Teleport to="#dbContentTitleAppend">
      <div class="inspection-todo-page-title-icon">
        <DbIcon
          v-bk-tooltips="titleTooltip"
          type="attention" />
      </div>
    </Teleport>
    <Teleport to="#dbContentHeaderAppend">
      <div class="inspection-todo-page-head-controls-main">
        <div
          class="tab-item tab-item-todo"
          :class="{ 'tab-item-active': currentActiveTab === 'todo' }"
          @click="() => handleClickTab('todo')">
          <DbIcon
            class="control-icon"
            type="wodedaiban" />
          <span>{{ t('待我处理') }}</span>
          <span> （{{ manageCount }}）</span>
        </div>
        <div
          class="tab-item tab-item-assist"
          :class="{ 'tab-item-active': currentActiveTab !== 'todo' }"
          @click="() => handleClickTab('assist')">
          <DbIcon
            class="control-icon"
            type="yonghu-2" />
          <span>{{ t('待我协助') }}</span>
          <span>（{{ assistCount }}）</span>
        </div>
      </div>
    </Teleport>
    <InspectionReportPage />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useReportCount } from '@hooks';

  import InspectionReportPage from '../report/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { manageCount, assistCount } = useReportCount();

  const currentActiveTab = ref(route.query.manage || 'todo');

  const titleTooltip = `${t('待我处理')}：${t('展示我作为主 DBA 的业务，当日所产生的巡检异常，一般每日更新一次')}\n${t('待我协助')}：${t('展示我作为备 DBA、二线 DBA 的业务，当日所产生的巡检异常，一般每日更新一次')}`;

  const handleClickTab = (tab: string) => {
    currentActiveTab.value = tab;
    router.replace({
      name: 'InspectionTodos',
      query: {
        ...route.query,
        manage: tab,
      },
    });
  };
</script>
<style lang="less">
  .inspection-todo-page-title-icon {
    display: flex;
    margin-right: 12px;
    margin-left: 6px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    align-items: center;
  }

  .inspection-todo-page-head-controls-main {
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
      padding: 0 5px 0 8px;
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
