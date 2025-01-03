<template>
  <FunController module-id="redis">
    <BkMenuGroup name="Redis">
      <BkSubmenu key="RedisManage">
        <template #icon>
          <DbIcon type="fenbushijiqun" />
        </template>
        <template #title>
          <span>{{ t('集群') }}</span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="cluster" />
        </template>
        <BkMenuItem key="DatabaseRedisList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群管理') }}
          </span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="cluster" />
        </BkMenuItem>
        <BkMenuItem
          key="DatabaseRedisInstanceList"
          v-db-console="'redis.instanceManage'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="instance" />
        </BkMenuItem>
      </BkSubmenu>
      <BkSubmenu
        key="RedisHaManage"
        v-db-console="'redis.haClusterManage'">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <template #title>
          <span>{{ t('主从') }}</span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="cluster" />
        </template>
        <BkMenuItem key="DatabaseRedisHaList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('主从管理') }}
          </span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="cluster" />
        </BkMenuItem>
        <BkMenuItem
          key="DatabaseRedisHaInstanceList"
          v-db-console="'redis.haInstanceManage'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="instance" />
        </BkMenuItem>
      </BkSubmenu>
      <div
        v-if="Object.keys(favorMeunMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'redis.toolbox'"
        :favor-map="favorMeunMap"
        :toolbox-menu-config="menuChildList" />
      <FunController
        controller-id="toolbox"
        module-id="redis">
        <BkMenuItem
          key="RedisToolbox"
          v-db-console="'redis.toolbox'">
          <template #icon>
            <DbIcon type="tools" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('工具箱') }}
          </span>
        </BkMenuItem>
      </FunController>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { onBeforeUnmount, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/db-manage/redis/toolbox-menu';

  import { makeMap } from '@utils';

  import CountTag from './components/CountTag.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  // const menuChildList = _.flatten(toolboxMenuConfig.map((item) => item.menuList));

  // TODO 暂时先做特殊处理至同层级，后期等设计稿交互变更
  const commonMenuList = _.cloneDeep(toolboxMenuConfig[0]);
  const manageItem = commonMenuList.menuList.find((item) => item.id === 'common-manage');
  manageItem!.children.push(...toolboxMenuConfig[1].menuList[0].children);
  const menuChildList = commonMenuList.menuList;

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value =
      userProfile.profile[UserPersonalSettings.REDIS_TOOLBOX_MENUS] || menuChildList.map((item) => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.REDIS_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('REDIS_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('REDIS_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
