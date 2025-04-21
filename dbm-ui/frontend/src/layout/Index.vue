<template>
  <BkNavigation
    :default-open="isSideMenuFlod"
    navigation-type="top-bottom"
    :need-menu="needMenu"
    :side-title="t('数据库管理')"
    @toggle-click="handleCollapse">
    <template #side-header>
      <span>
        <img
          height="30"
          src="@images/nav-logo.png"
          width="30" />
        <span class="title-desc ml-8">{{ t('数据库管理') }}</span>
      </span>
    </template>
    <template #header>
      <div class="db-navigation-header">
        <div
          v-for="menuItem in menuList"
          :key="menuItem.value"
          v-db-console="menuItem.dbConsoleValue"
          class="nav-item"
          :class="{
            active: menuType === menuItem.value,
          }"
          @click="handleMenuChange(menuItem.value)">
          {{ menuItem.label }}
        </div>
      </div>
      <div class="db-navigation-header-right">
        <slot name="navigationHeaderRight" />
      </div>
    </template>
    <template #menu>
      <component :is="renderMenuCom" />
    </template>
    <div class="db-navigation-content-header">
      <slot name="content-header" />
      <div class="db-navigation-content-title">
        {{ contentTitle }}
        <div id="dbContentTitleAppend" />
      </div>
      <div id="dbContentHeaderAppend" />
    </div>
    <div
      class="db-navigation-content-wrapper"
      :class="{ 'is-fullscreen': isContendFullscreen }"
      style="height: calc(100vh - var(--notice-height) - 104px)">
      <slot />
    </div>
  </BkNavigation>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { useUserProfile } from '@stores';

  import { useStorage } from '@vueuse/core';

  import ConfigManage from './components/ConfigManage.vue';
  import DatabaseManage from './components/database-manage/Index.vue';
  import GlobalConfigManage from './components/GlobalConfigManage.vue';
  import ObservableManage from './components/ObservableManage.vue';
  import PersonalWorkbench from './components/PersonalWorkbench.vue';
  import PlatformManage from './components/PlatformManage.vue';
  import ResourceManage from './components/ResourceManage.vue';

  const { t } = useI18n();
  const route = useRoute();
  const userProfile = useUserProfile();
  const isSideMenuFlod = useStorage('is_side_menu_flod', false);

  const enum menuEnum {
    configManage = 'configManage',
    databaseManage = 'databaseManage',
    globalConfigManage = 'globalConfigManage',
    observableManage = 'observableManage',
    personalWorkbench = 'personalWorkbench',
    platformManage = 'platformManage',
    resourceManage = 'resourceManage',
  }

  const menuList = [
    {
      dbConsoleValue: 'databaseManage',
      label: t('数据库管理'),
      value: menuEnum.databaseManage,
    },
    {
      dbConsoleValue: 'observableManage',
      label: t('可观测'),
      value: menuEnum.observableManage,
    },
    {
      dbConsoleValue: 'bizConfigManage',
      label: t('业务配置'),
      value: menuEnum.configManage,
    },
    userProfile.resourceManage && {
      dbConsoleValue: 'resourceManage',
      label: t('资源管理'),
      value: menuEnum.resourceManage,
    },
    userProfile.globalManage && {
      dbConsoleValue: 'globalConfigManage',
      label: t('全局配置'),
      value: menuEnum.globalConfigManage,
    },
    userProfile.platformManage && {
      label: t('平台管理'),
      value: menuEnum.platformManage,
    },
    {
      dbConsoleValue: 'personalWorkbench',
      label: t('个人工作台'),
      value: menuEnum.personalWorkbench,
    },
  ].filter((item) => item) as {
    dbConsoleValue: string;
    label: string;
    value: string;
  }[];

  const routeGroup = {
    [menuEnum.configManage]: [
      'BizResourcePool',
      'BizResourceTag',
      'DbConfigure',
      'DBMonitorStrategy',
      'DBMonitorAlarmGroup',
      'AlarmShield',
      'StaffManage',
      'TicketFlowSetting',
      'TicketCooperationSetting',
      'TicketNoticeSetting',
    ],
    [menuEnum.databaseManage]: [
      'MysqlManage',
      'EsManage',
      'HdfsManage',
      'InfluxDBManage',
      'KafkaManage',
      'PulsarManage',
      'RedisManage',
      'SpiderManage',
      'RiakManage',
      'MongoDBManage',
      'SqlServerManage',
      'DorisManage',
      'taskHistory',
      'DatabaseWhitelist',
      'bizTicketManage',
      'DBPasswordTemporaryModify',
    ],
    [menuEnum.globalConfigManage]: [
      'PlatformVersionFiles',
      'PlatformDbConfigure',
      'PlatformWhitelist',
      'PlatGlobalStrategy',
      'dutyRuleManange',
      'PlatformNotificationSetting',
      'passwordManage',
      'PlatformTicketFlowSetting',
      'PlatformStaffManage',
    ],
    [menuEnum.observableManage]: ['DBHASwitchEvents', 'inspectionManage', 'AlarmManage'],
    [menuEnum.personalWorkbench]: [
      'serviceApply',
      'SelfServiceMyTickets',
      'MyTodos',
      'ticketSelfDone',
      'ticketSelfManage',
      'InspectionTodos',
      'AlarmEventsTodo',
    ],
    [menuEnum.platformManage]: [
      'platformTaskManage',
      'ticketPlatformManage',
      'inspectionReportGlobal',
      'DbaManage',
      'AlarmEventsGlobal',
    ],
    [menuEnum.resourceManage]: ['ResourceSpec', 'resourceManage', 'resourcePoolDirtyMachines'],
  } as Record<string, string[]>;

  const menuType = ref('');

  const renderMenuCom = computed(() => {
    const comMap = {
      configManage: ConfigManage,
      databaseManage: DatabaseManage,
      globalConfigManage: GlobalConfigManage,
      [menuEnum.platformManage]: PlatformManage,
      observableManage: ObservableManage,
      personalWorkbench: PersonalWorkbench,
      resourceManage: ResourceManage,
    };
    return comMap[menuType.value as keyof typeof comMap];
  });
  const contentTitle = computed(() => route.meta.navName);
  const isContendFullscreen = computed(() => Boolean(route.meta.fullscreen));
  // 全局搜索结果页面不显示，点击顶部导航栏后显示并自动跳转
  const needMenu = computed(() => Boolean(menuType.value));

  // 解析路由分组
  watch(
    route,
    () => {
      if (route.name === 'index') {
        menuType.value = menuEnum.databaseManage;
        return;
      }

      const routeGroupMap = Object.keys(routeGroup).reduce(
        (result, key) => {
          routeGroup[key].forEach((item) => {
            Object.assign(result, {
              [item]: key,
            });
          });
          return result;
        },
        {} as Record<string, string>,
      );
      _.forEach(route.matched, (item) => {
        const routeName = item.name as string;
        if (routeName && routeGroupMap[routeName]) {
          menuType.value = routeGroupMap[routeName];
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleCollapse = () => {
    isSideMenuFlod.value = !isSideMenuFlod.value;
    console.log('handleCollapse');
  };

  const handleMenuChange = (type: string) => {
    menuType.value = type;
  };
</script>
<style lang="less">
  .bk-navigation {
    height: calc(100vh - var(--notice-height)) !important;

    .container-content {
      height: auto;
      max-height: unset !important;
      padding: 0 !important;
    }

    .navigation-nav {
      z-index: 1001 !important;

      .split-line {
        margin: 0 20px 0 60px;
        border-bottom: solid #29344c 1px;
      }

      .nav-slider {
        border: none !important;
      }

      .group-name {
        color: #fff;
      }
    }

    .navigation-container {
      max-width: none !important;

      .container-content {
        max-height: calc(100vh - 52px - var(--notice-height)) !important;
      }
    }

    .bk-navigation-header {
      background: #0e1525;
    }
  }

  .db-navigation-header {
    display: flex;
    white-space: nowrap;

    .nav-item {
      position: relative;
      padding: 0 16px;
      color: #96a2b9;
      cursor: pointer;
      transition: 0.1s;

      &.active,
      &:hover {
        color: #fff;
      }

      &:last-child {
        position: relative;

        &::before {
          position: absolute;
          top: 50%;
          left: 0;
          width: 1px;
          height: 12px;
          background: #434853;
          content: '';
          transform: translateY(-50%);
        }
      }
    }
  }

  .db-navigation-header-right {
    display: flex;
    flex: 1;
    margin-left: 80px;
    color: #979ba5;
    align-items: center;
    justify-content: flex-end;
  }

  .db-navigation-content-header {
    position: relative;
    z-index: 99;
    display: flex;
    height: 52px;
    padding: 0 14px;
    background: #fff;
    align-content: center;
    box-shadow: 0 3px 4px 0 #0000000a;

    #dbContentHeaderAppend {
      flex: 1;
      display: flex;
      align-items: center;
      color: #313238;
    }
  }

  .db-navigation-content-title {
    display: flex;
    font-size: 16px;
    color: #313238;
    align-items: center;
  }

  .db-navigation-content-wrapper {
    padding: 20px 24px 0;
    overflow: auto;

    &.is-fullscreen {
      padding: 0;
    }
  }
</style>
