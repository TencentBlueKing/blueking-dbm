<template>
  <BkMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <BkMenuGroup :name="t('个人工作台')">
      <BkMenuItem key="serviceApply">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('服务申请') }}
        </span>
      </BkMenuItem>
      <BkMenuItem key="SelfServiceMyTickets">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('我的服务单') }}
        </span>
      </BkMenuItem>
      <BkMenuItem key="MyTodos">
        <template #icon>
          <DbIcon type="todos" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('我的待办') }}
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

