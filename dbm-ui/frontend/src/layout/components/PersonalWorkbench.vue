<template>
  <BkMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <BkMenuGroup
      v-db-console="'personalWorkbench'"
      :name="t('个人工作台')">
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
      <BkMenuItem
        key="SelfServiceMyTickets"
        v-db-console="'personalWorkbench.myTickets'">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('我的申请') }}
        </span>
      </BkMenuItem>
      <BkMenuItem
        key="MyTodos"
        v-db-console="'personalWorkbench.myTodos'">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('我的待办') }}
        </span>
      </BkMenuItem>
      <BkMenuItem
        key="ticketSelfManage"
        v-db-console="'personalWorkbench.myTickets'">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('我负责的业务') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
  </BkMenu>
</template>
<script setup lang="ts">
  import { Menu } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { useActiveKey } from './hooks/useActiveKey';

  const { t } = useI18n();

  const menuRef = ref<InstanceType<typeof Menu>>();

  const {
    parentKey,
    key: currentActiveKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'serviceApply');
</script>
