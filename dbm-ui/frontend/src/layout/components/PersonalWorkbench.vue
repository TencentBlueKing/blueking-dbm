<template>
  <BkMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <BkMenuGroup
      v-db-console="'personalWorkbench'"
      :name="t('我的待办')">
      <BkMenuItem
        key="MyTodos"
        v-db-console="'personalWorkbench.myTodos'">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span>
          {{ t('单据待办') }}
        </span>
        <span class="ticket-count">{{ todoCount }}</span>
      </BkMenuItem>
      <BkMenuItem
        v-if="userProfileStore.isDba"
        key="InspectionTodos"
        v-db-console="'personalWorkbench.InspectionTodos'">
        <template #icon>
          <DbIcon type="cluster-standardize" />
        </template>
        <span>
          {{ t('巡检待办') }}
        </span>
        <span class="ticket-count">{{ manageCount }}</span>
      </BkMenuItem>
    </BkMenuGroup>
    <BkMenuGroup
      v-db-console="'personalWorkbench'"
      :name="t('我的申请')">
      <BkMenuItem
        key="SelfServiceMyTickets"
        v-db-console="'personalWorkbench.myTickets'">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        <span>
          {{ t('我的申请') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
    <BkMenuGroup
      v-db-console="'personalWorkbench'"
      :name="t('我的已办')">
      <BkMenuItem
        key="ticketSelfDone"
        v-db-console="'personalWorkbench.myTickets'">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span>
          {{ t('已办单据') }}
        </span>
      </BkMenuItem>
      <!-- <BkMenuGroup>
      v-db-console="'personalWorkbench'"
      :name="t('单据管理')">
      <BkMenuItem
        key="ticketSelfManage"
        v-db-console="'personalWorkbench.myTickets'">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span>
          {{ t('我负责的业务') }}
        </span>
      </BkMenuItem> 
      </BkMenuGroup>-->
      <BkMenuItem
        key="serviceApply"
        v-db-console="'personalWorkbench.serviceApply'">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('服务申请') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </BkMenu>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { useReportCount, useTicketCount } from '@hooks';

  import { useUserProfile } from '@stores';

  import { useActiveKey } from './hooks/useActiveKey';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'MyTodos');

  const { data: ticketCount } = useTicketCount();
  const { manageCount } = useReportCount();
  const userProfileStore = useUserProfile();

  const todoCount = computed(() => {
    if (!ticketCount.value) {
      return 0;
    }

    return (
      ticketCount.value.pending.APPROVE +
      ticketCount.value.pending.FAILED +
      ticketCount.value.pending.RESOURCE_REPLENISH +
      ticketCount.value.pending.INNER_TODO +
      ticketCount.value.pending.TODO
    );
  });
</script>
<style lang="less">
  .bk-menu-item {
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

    &.is-active {
      .ticket-count {
        color: #3a84ff;
        background: #e1ecff;
        transition: all 0.1s;
      }
    }
  }
</style>
