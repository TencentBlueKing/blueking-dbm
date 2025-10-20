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
    <BkMenuGroup :name="t('异常中心')">
      <BkMenuItem key="platformAlarmEvents">
        <template #icon>
          <DbIcon type="db-config" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('告警事件') }}
        </span>
      </BkMenuItem>
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
      <BkMenuItem key="RiskMemoGlobal">
        <template #icon>
          <DbIcon type="file" />
        </template>
        {{ t('风险备忘录') }}
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
    <!-- <BkMenuGroup
      v-db-console="'platformManage.healthReport'"
      :name="t('巡检')">
    </BkMenuGroup> -->
    <!-- <BkMenuGroup
      v-db-console="'platformManage.AlarmEvents'"
      :name="t('告警')">
    </BkMenuGroup> -->
    <BkMenuGroup
      v-if="dashboardList && dashboardList.length > 0"
      :name="t('运营数据')">
      <BkMenuItem
        v-for="dashboardItem in dashboardList"
        :key="`DashboradView#${dashboardItem.uid}`">
        <template #icon>
          <DbIcon type="ticket" />
        </template>
        {{ dashboardItem.name }}
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
<script setup lang="ts" async>
  import { Menu } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getAppShareList } from '@services/source/bkVersion';

  import { useFunController } from '@stores';

  import { useActiveKey } from './hooks/useActiveKey';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const funControllerStore = useFunController();

  const menuRef = ref<InstanceType<typeof Menu>>();

  const { data: dashboardList, runAsync: fetchAppShareList } = useRequest(getAppShareList, {
    manual: true,
  });

  if (funControllerStore.funControllerData.getFlatData('dashboard').dashboard) {
    await fetchAppShareList();
  }

  const { key: currentActiveKey, parentKey } = useActiveKey(
    menuRef as Ref<InstanceType<typeof Menu>>,
    'ticketPlatformManage',
    {
      checkMethod: (routerName: string) => {
        if (routerName === 'DashboradView') {
          return `DashboradView#${route.params.versionId}`;
        }
        return routerName;
      },
    },
  );

  const handleMenuChange = (params: { key: string }) => {
    if (params.key.startsWith('DashboradView')) {
      const [, versionId] = params.key.split('#');
      router.push({
        name: 'DashboradView',
        params: {
          versionId,
        },
      });
      return;
    }
    router.push({
      name: params.key,
    });
  };
</script>
