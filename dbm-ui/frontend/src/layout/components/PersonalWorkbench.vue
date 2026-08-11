<template>
  <DbMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <DbMenuGroup
      v-db-console="'personalWorkbench'"
      :fold-name="t('待办')"
      :name="t('我的待办')">
      <DbMenuItem
        v-db-console="'personalWorkbench.myTodos'"
        icon="todos"
        route-name="MyTodos">
        {{ t('单据待办') }}
        <template #append>
          <span class="ticket-count">{{ ticketTodoCount }}</span>
        </template>
      </DbMenuItem>
      <DbMenuItem
        v-if="userProfileStore.isDba"
        v-db-console="'personalWorkbench.platformAlarmEventsTodo'"
        icon="warning"
        route-name="platformAlarmEventsTodo">
        {{ t('告警事件待办') }}
        <template #append>
          <span class="ticket-count">{{ alarmEventsTodoCount }}</span>
        </template>
      </DbMenuItem>
      <DbMenuItem
        v-if="userProfileStore.isDba"
        v-db-console="'personalWorkbench.InspectionTodos'"
        icon="cluster-standardize"
        route-name="inspectionTodosGlobal">
        {{ t('巡检待办') }}
        <template #append>
          <span class="ticket-count">{{ reportManageCount }}</span>
        </template>
      </DbMenuItem>
      <DbMenuItem
        v-if="userProfileStore.isDba"
        v-db-console="'personalWorkbench.hostTodo'"
        icon="host"
        route-name="resourceManageHostTodo">
        {{ t('主机处理待办') }}
        <template #append>
          <span class="ticket-count">{{ hostTodoCount }}</span>
        </template>
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'personalWorkbench.clusterDisableTodo'"
        icon="todos"
        route-name="ClusterDisableTodo">
        {{ t('集群下架待办') }}
        <template #append>
          <span class="ticket-count">{{ clusterDisableTodoCount + clusterDisableToAssistCount }}</span>
        </template>
      </DbMenuItem>
      <DbMenuItem
        v-if="userProfileStore.isDba"
        v-db-console="'personalWorkbench.RiskMemoTodos'"
        icon="file"
        route-name="RiskMemoTodos">
        {{ t('风险备忘录') }}
        <template #append>
          <span class="ticket-count">{{ riskMemoTodoCount }}</span>
        </template>
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-db-console="'personalWorkbench'"
      :fold-name="t('申请')"
      :name="t('我的申请')">
      <DbMenuItem
        v-db-console="'personalWorkbench.myTickets'"
        icon="ticket"
        route-name="SelfServiceMyTickets">
        {{ t('我的申请') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-db-console="'personalWorkbench'"
      :fold-name="t('已办')"
      :name="t('我的已办')">
      <DbMenuItem
        v-db-console="'personalWorkbench.myTickets'"
        icon="todos"
        route-name="ticketSelfDone">
        {{ t('已办单据') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-db-console="'personalWorkbench'"
      :name="t('订阅')">
      <DbMenuItem
        v-db-console="'personalWorkbench.myAlarmSubscription'"
        icon="note"
        route-name="myAlarmSubscription">
        {{ t('我的告警订阅') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-db-console="'personalWorkbench'"
      :fold-name="t('部署')"
      :name="t('数据库部署')">
      <DbMenuItem
        v-db-console="'personalWorkbench.serviceApply'"
        icon="ticket"
        route-name="serviceApply">
        {{ t('部署申请') }}
      </DbMenuItem>
    </DbMenuGroup>
  </DbMenu>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    useAlarmEventsCount,
    useClusterDisableCount,
    useHostTodoCount,
    useReportCount,
    useRiskMemoCount,
    useTicketCount,
  } from '@hooks';

  import { useUserProfile } from '@stores';

  import { useActiveKey } from './hooks/useActiveKey';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof DbMenu>>();

  const { key: currentActiveKey, parentKey, routeLocation: handleMenuChange } = useActiveKey(menuRef, 'MyTodos');

  const userProfileStore = useUserProfile();
  const { data: ticketCount } = useTicketCount();
  const { toAssistCount: clusterDisableToAssistCount, todoCount: clusterDisableTodoCount } = useClusterDisableCount();
  const { totalCount: hostTodoCount } = useHostTodoCount();
  const { todoCount: alarmEventsTodoCount } = useAlarmEventsCount();
  const { todoCount: riskMemoTodoCount } = useRiskMemoCount();
  const { manageCount: reportManageCount } = useReportCount(userProfileStore.isDba);

  const ticketTodoCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.pending.APPROVE +
      ticketCount.value.pending.FAILED +
      ticketCount.value.pending.RESOURCE_REPLENISH +
      ticketCount.value.pending.INNER_TODO +
      ticketCount.value.pending.TIMER +
      ticketCount.value.pending.TODO
    );
  });
</script>
<style lang="less">
  .ticket-count {
    display: inline-block;
    height: 16px;
    padding: 0 8px;
    margin-left: 4px;
    font-size: 12px;
    line-height: 16px;
    color: #fff;
    background: #333a47;
    border-radius: 8px;
  }

  .db-menu-item.is-active {
    .ticket-count {
      color: #3a84ff;
      background: #e1ecff;
      transition: all 0.1s;
    }
  }
</style>
