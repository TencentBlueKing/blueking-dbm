<template>
  <DbMenu
    ref="menuRef"
    :active-key="currentActiveKey"
    :opened-keys="[parentKey]"
    @click="handleMenuChange">
    <DbMenuGroup
      :fold-name="t('单据')"
      :name="t('单据中心')">
      <DbMenuItem
        icon="danju-2"
        route-name="ticketPlatformManage">
        {{ t('单据') }}
      </DbMenuItem>
      <DbMenuItem
        icon="renwu-2"
        route-name="platformTaskManage">
        {{ t('任务') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-db-console="'platformManage.dbaManage'"
      :fold-name="t('工具')"
      :name="t('DBA 工具箱')">
      <DbMenuItem
        v-if="ENABLE_DBM_AI"
        icon="dbazhinengzhushou"
        route-name="AgentChat">
        {{ t('DBA 智能助手') }}
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'platformManage.dbaManage.mysql'"
        icon="mysql"
        route-name="DbaManageMysql">
        MySQL
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'platformManage.dbaManage.tendbCluster'"
        icon="tendbcluster"
        route-name="DbaManageTendbCluster">
        Tendb Cluster
      </DbMenuItem>
      <DbMenuItem
        v-db-console="'platformManage.dbaManage.redis'"
        icon="redis"
        route-name="DbaManageRedis">
        Redis
      </DbMenuItem>
      <DbMenuItem
        icon="sqlserver"
        route-name="DbaManageSQLServerWebQuery">
        SQLServer
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      :fold-name="t('异常')"
      :name="t('异常中心')">
      <DbMenuItem
        icon="gaojing"
        route-name="platformAlarmEvents">
        {{ t('告警事件') }}
      </DbMenuItem>
      <DbMenuItem
        icon="xunjianbaogao"
        route-name="inspectionReportGlobal">
        {{ t('巡检报告') }}
      </DbMenuItem>
      <DbMenuItem
        icon="yanlianbaogao-2"
        route-name="ExerciseReportGlobal">
        {{ t('演练报告') }}
      </DbMenuItem>
      <DbMenuItem
        icon="fengxianbaowanglu"
        route-name="RiskMemoGlobal">
        {{ t('风险备忘录') }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      v-if="dashboardList && dashboardList.length > 0"
      :fold-name="t('运营')"
      :name="t('运营数据')">
      <DbMenuItem
        v-for="dashboardItem in dashboardList"
        :key="dashboardItem.uid"
        :icon="dashboardIconMap[dashboardItem.name] || 'yunyingshuju'"
        :route-name="`DashboradView#${dashboardItem.uid}`">
        {{ dashboardItem.name }}
      </DbMenuItem>
    </DbMenuGroup>
    <DbMenuGroup
      :fold-name="t('观测')"
      :name="t('平台观测')">
      <DbMenuItem
        icon="fuwuzhuangtai"
        route-name="ServiceStatus">
        {{ t('服务状态') }}
      </DbMenuItem>
    </DbMenuGroup>
  </DbMenu>
</template>
<script setup lang="ts" async>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getAppShareList } from '@services/source/bkVersion';

  import { useFunController, useSystemEnviron } from '@stores';

  import { useActiveKey } from './hooks/useActiveKey';
  import DbMenuGroup from './menu/Group.vue';
  import DbMenu from './menu/Index.vue';
  import DbMenuItem from './menu/Item.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const funControllerStore = useFunController();
  const systemEnvironStore = useSystemEnviron();
  const { ENABLE_DBM_AI } = systemEnvironStore.urls;

  const menuRef = ref<InstanceType<typeof DbMenu>>();

  // 运营数据看板名称 -> 菜单图标映射，未命中默认取 ticket
  const dashboardIconMap: Record<string, string> = {
    'DBA-AI工时': 'dba-aigongshi',
    'DBA(武汉)': 'dba-config',
    'DBA(深圳)': 'dba-config',
    单据: 'danju-2',
    可靠: 'kekao',
    告警: 'gaojing',
    平台观测数据: 'pingtaiguanceshuju',
    概览: 'gailan',
    版本: 'version',
    负载: 'fuzai',
    资源: 'ziyuan',
  };

  const { data: dashboardList, runAsync: fetchAppShareList } = useRequest(getAppShareList, {
    manual: true,
  });

  if (funControllerStore.funControllerData.getFlatData('dashboard').dashboard) {
    await fetchAppShareList();
  }

  const { key: currentActiveKey, parentKey } = useActiveKey(menuRef, 'ticketPlatformManage', {
    checkMethod: (routerName: string) => {
      if (routerName === 'DashboradView') {
        return `DashboradView#${route.params.versionId}`;
      }
      return routerName;
    },
  });

  const handleMenuChange = (routeName: string) => {
    if (routeName.startsWith('DashboradView')) {
      const [, versionId] = routeName.split('#');
      router.push({
        name: 'DashboradView',
        params: {
          versionId,
        },
      });
      return;
    }
    router.push({
      name: routeName,
    });
  };
</script>
