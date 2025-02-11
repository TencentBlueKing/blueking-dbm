<template>
  <BkMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <BkMenuGroup :name="t('单据中心')">
      <BkMenuItem key="ticketPlatformManage">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        {{ t('单据') }}
      </BkMenuItem>
      <BkMenuItem key="platformTaskManage">
        <template #icon>
          <DbIcon type="history" />
        </template>
        {{ t('任务') }}
      </BkMenuItem>
    </BkMenuGroup>
    <BkMenuGroup
      v-db-console="'platformManage.healthReport'"
      :name="t('巡检')">
      <BkMenuItem key="inspectionReportGlobal">
        <template #icon>
          <DbIcon type="db-config" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('巡检报告') }}
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
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'ticketPlatformManage');
</script>
