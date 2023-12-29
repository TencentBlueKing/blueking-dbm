<template>
  <BkNavigation
    :default-open="isSideMenuFlod"
    navigation-type="top-bottom"
    :side-title="t('数据库管理')"
    @toggle="handleCollapse">
    <template #side-header>
      <span>
        <img
          height="30"
          src="@images/nav-logo.png"
          width="30">
        <span class="title-desc ml-8">{{ t('数据库管理') }}</span>
      </span>
    </template>
    <template #header>
      <div class="db-navigation-header">
        <div
          v-for="menuItem in menuList"
          :key="menuItem.value"
          class="nav-item"
          :class="{
            active: menuType === menuItem.value
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
      :class="{'is-fullscreen': isContendFullscreen}">
      <slot />
    </div>
  </BkNavigation>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import ConfigManage from './components/ConfigManage.vue';
  import DatabaseManage from './components/database-manage/Index.vue';
  import ObservableManage from './components/ObservableManage.vue';
  import PersonalWorkbench from './components/PersonalWorkbench.vue';
  import PlatformManage from './components/PlatformManage.vue';
  import ResourceManage from './components/ResourceManage.vue';


  const SIDE_MENU_TOGGLE_KEY = 'sideMenuFlod';
  const { t } = useI18n();
  const route = useRoute();

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
    },
    {
      label: t('可观测'),
      value: menuEnum.observableManage,
    },
    {
      label: t('配置管理'),
      value: menuEnum.configManage,
    },
    {
      label: t('资源管理'),
      value: menuEnum.resourceManage,
    },
    {
      label: t('平台管理'),
      value: menuEnum.platformManage,
    },
    {
      label: t('个人工作台'),
      value: menuEnum.personalWorkbench,
    },
  ];

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
      'taskHistory',
      'DatabaseWhitelist',
      'ticketManage',
      'DBPasswordTemporaryModify',
    ],
    [menuEnum.observableManage]: [
      'DBHASwitchEvents',
      'inspectionManage',
    ],
    [menuEnum.configManage]: [
      'DbConfigure',
      'DBMonitorStrategy',
      'DBMonitorAlarmGroup',
      'DatabaseStaff',
    ],
    [menuEnum.resourceManage]: [
      'ResourceSpec',
      'resourceManage',
      'resourcePoolDirtyMachines',
    ],
    [menuEnum.platformManage]: [
      'PlatformVersionFiles',
      'PlatformDbConfigure',
      'PlatformWhitelist',
      'PlatGlobalStrategy',
      'PlatRotateSet',
      'PlatMonitorAlarmGroup',
      'passwordManage',
    ],
    [menuEnum.personalWorkbench]: [
      'SelfServiceMyTickets',
      'MyTodos',
      'serviceApply',
    ],
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

  // 解析路由分组
  watch(route, () => {
    if (route.name === 'index') {
      menuType.value = menuEnum.databaseManage;
      return;
    }

    const routeGroupMap = Object.keys(routeGroup).reduce((result, key) => {
      routeGroup[key].forEach((item) => {
        Object.assign(result, {
          [item]: key,
        });
      });
      return result;
    }, {} as Record<string, string>);
    _.forEach(route.matched, (item) => {
      const routeName = item.name as string;
      if (routeName && routeGroupMap[routeName]) {
        menuType.value = routeGroupMap[routeName];
      }
    });
  }, {
    immediate: true,
  });

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
.bk-navigation{
  .container-content{
    height: auto;
    max-height: unset !important;
    padding: 0 !important;
  }

  .navigation-nav{
    .split-line{
      margin: 0 20px 0 60px;
      border-bottom: solid #29344c 1px;
    }

    .nav-slider{
      border: none !important;
    }

    .group-name {
      color: #fff;
    }
  }
}

.db-navigation-header{
  display: flex;

  .nav-item{
    position: relative;
    padding: 0 16px;
    color: #96A2B9;
    cursor: pointer;
    transition: 0.1s;

    &.active,
    &:hover{
      color: #FFF;
    }

    &:last-child{
      position: relative;

      &::before{
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

.db-navigation-header-right{
  display: flex;
  flex: 1;
  margin-left: 80px;
  color: #979BA5;
  align-items: center;
}

.db-navigation-content-header{
  position: relative;
  z-index: 1;
  display: flex;
  height: 52px;
  padding: 0 14px;
  background: #FFF;
  box-shadow: 0 3px 4px 0 #0000000a;
  align-content: center;

  #dbContentHeaderAppend{
    flex: 1;
    display: flex;
    align-items: center;
  }
}

.db-navigation-content-title{
  display: flex;
  font-size: 16px;
  color: #313238;
  align-items: center;
}

.db-navigation-content-wrapper{
  height: calc(100vh - 104px);
  padding: 20px 24px 0;
  overflow: auto;

  &.is-fullscreen{
    padding: 0;
  }
}
</style>

