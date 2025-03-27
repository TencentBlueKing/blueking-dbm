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
      v-db-console="'platformManage.dbaManage'"
      :name="t('DBA 工具箱')">
      <BkMenuItem
        key="DbaManageMysql"
        v-db-console="'platformManage.dbaManage.mysql'">
        <template #icon>
          <DbIcon type="mysql" />
        </template>
        MySQL
      </BkMenuItem>
      <BkMenuItem
        key="DbaManageTendbCluster"
        v-db-console="'platformManage.dbaManage.tendbCluster'">
        <template #icon>
          <DbIcon type="mysql" />
        </template>
        Tendb Cluster
      </BkMenuItem>
      <BkMenuItem
        key="DbaManageRedis"
        v-db-console="'platformManage.dbaManage.redis'">
        <template #icon>
          <DbIcon type="redis" />
        </template>
        Redis
      </BkMenuItem>
      <BkMenuItem key="DbaManageSQLServerWebQuery">
        <template #icon>
          <DbIcon type="sqlserver" />
        </template>
        SQLServer
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
    <BkMenuGroup
      v-db-console="'platformManage.AlarmEvents'"
      :name="t('告警')">
      <BkMenuItem key="AlarmEventsGlobal">
        <template #icon>
          <DbIcon type="db-config" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('告警事件') }}
        </span>
      </BkMenuItem>
    </BkMenuGroup>
    <BkMenuGroup :name="t('平台观测')">
      <BkMenuItem key="ServiceStatus">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        {{ t('服务状态') }}
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
    key: currentActiveKey,
    parentKey,
    routeLocation: handleMenuChange,
  } = useActiveKey(menuRef as Ref<InstanceType<typeof Menu>>, 'ticketPlatformManage');
</script>
