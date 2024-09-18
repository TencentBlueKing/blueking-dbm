<template>
  <BkNavigation
    :default-open="isSideMenuFlod"
    navigation-type="top-bottom"
    :need-menu="needMenu"
    :side-title="t('数据库管理')"
    @toggle="handleCollapse">
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

  import ConfigManage from './components/ConfigManage.vue';
  import DatabaseManage from './components/database-manage/Index.vue';
  import ObservableManage from './components/ObservableManage.vue';
  import PersonalWorkbench from './components/PersonalWorkbench.vue';
  import PlatformManage from './components/PlatformManage.vue';
  import ResourceManage from './components/ResourceManage.vue';

  const SIDE_MENU_TOGGLE_KEY = 'sideMenuFlod';
  const { t } = useI18n();
  const route = useRoute();
  const userProfile = useUserProfile();

  const enum menuEnum {
    databaseManage = 'databaseManage',
    observableManage = 'observableManage',
    configManage = 'configManage',
    resourceManage = 'resourceManage',
    platformManage = 'platformManage',
    personalWorkbench = 'personalWorkbench',
  }

  const menuList = [
    {
      label: t('数据库管理'),
      value: menuEnum.databaseManage,
      dbConsoleValue: 'databaseManage',
    },
    {
      label: t('可观测'),
      value: menuEnum.observableManage,
      dbConsoleValue: 'observableManage',
    },
    {
      label: t('业务配置'),
      value: menuEnum.configManage,
      dbConsoleValue: 'bizConfigManage',
    },
    userProfile.rerourceManage && {
      label: t('资源管理'),
      value: menuEnum.resourceManage,
      dbConsoleValue: 'resourceManage',
    },
    userProfile.globalManage && {
      label: t('全局配置'),
      value: menuEnum.platformManage,
      dbConsoleValue: 'globalConfigManage',
    },
    {
      label: t('个人工作台'),
      value: menuEnum.personalWorkbench,
      dbConsoleValue: 'personalWorkbench',
    },
  ].filter((item) => item) as {
    label: string;
    value: string;
    dbConsoleValue: string;
  }[];

  const routeGroup = {
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
      'taskHistory',
      'DatabaseWhitelist',
      'ticketManage',
      'DBPasswordTemporaryModify',
    ],
    [menuEnum.observableManage]: ['DBHASwitchEvents', 'inspectionManage'],
    [menuEnum.configManage]: [
      'DbConfigure',
      'DBMonitorStrategy',
      'DBMonitorAlarmGroup',
      'StaffManage',
      'TicketFlowSetting',
    ],
    [menuEnum.resourceManage]: ['ResourceSpec', 'resourceManage', 'resourcePoolDirtyMachines'],
    [menuEnum.platformManage]: [
      'PlatformVersionFiles',
      'PlatformDbConfigure',
      'PlatformWhitelist',
      'PlatGlobalStrategy',
      'dutyRuleManange',
      // 'PlatMonitorAlarmGroup',
      'PlatformNotificationSetting',
      'passwordManage',
      'PlatformTicketFlowSetting',
      'PlatformStaffManage',
    ],
    [menuEnum.personalWorkbench]: ['SelfServiceMyTickets', 'MyTodos', 'serviceApply', 'ticketSelfManage'],
  } as Record<string, string[]>;

  const menuType = ref('');
  const isSideMenuFlod = ref(localStorage.getItem(SIDE_MENU_TOGGLE_KEY) !== null);

  const renderMenuCom = computed(() => {
    const comMap = {
      databaseManage: DatabaseManage,
      observableManage: ObservableManage,
      configManage: ConfigManage,
      resourceManage: ResourceManage,
      platformManage: PlatformManage,
      personalWorkbench: PersonalWorkbench,
    };
    return comMap[menuType.value as keyof typeof comMap];
  });
  const contentTitle = computed(() => route.meta.navName);
  const isContendFullscreen = computed(() => Boolean(route.meta.fullscreen));
  // 全局搜索结果页面不显示，点击顶部导航栏后显示并自动跳转
  const needMenu = computed(() => !(route.name === 'QuickSearch' && menuType.value === ''));

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
    if (!isSideMenuFlod.value) {
      localStorage.setItem(SIDE_MENU_TOGGLE_KEY, 'open');
    } else {
      localStorage.removeItem(SIDE_MENU_TOGGLE_KEY);
    }
  };

  const handleMenuChange = (type: string) => {
    menuType.value = type;
  };
</script>
<style lang="less">
  .bk-navigation {
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
    }

    .bk-navigation-header {
      background: #0e1525;
    }
  }

  .db-navigation-header {
    display: flex;

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
    z-index: 999;
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
