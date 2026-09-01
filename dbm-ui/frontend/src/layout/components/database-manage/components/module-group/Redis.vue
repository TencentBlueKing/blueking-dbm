<template>
  <FunController module-id="redis">
    <MenuGroup
      :db-type="DBTypes.REDIS"
      :is-error="isError">
      <DbSubmenu
        id="RedisManage"
        icon="fenbushijiqun"
        :title="t('集群')">
        <template #append>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="cluster" />
        </template>
        <DbMenuItem route-name="redisCluster">
          {{ t('集群管理') }}
          <template #append>
            <!-- prettier-ignore -->
            <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="cluster" />
          </template>
        </DbMenuItem>
        <DbMenuItem
          v-db-console="'redis.instanceManage'"
          route-name="DatabaseRedisInstanceList">
          {{ t('实例视图') }}
          <template #append>
            <!-- prettier-ignore -->
            <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="instance" />
          </template>
        </DbMenuItem>
      </DbSubmenu>
      <DbSubmenu
        id="RedisHaManage"
        v-db-console="'redis.haClusterManage'"
        icon="cluster"
        :title="t('主从')">
        <template #append>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="cluster" />
        </template>
        <DbMenuItem route-name="DatabaseRedisHa">
          {{ t('主从管理') }}
          <template #append>
            <!-- prettier-ignore -->
            <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="cluster" />
          </template>
        </DbMenuItem>
        <DbMenuItem
          v-db-console="'redis.haInstanceManage'"
          route-name="DatabaseRedisHaInstanceList">
          {{ t('实例视图') }}
          <template #append>
            <!-- prettier-ignore -->
            <CountTag :cluster-type="('RedisInstance' as ClusterTypes)" role="instance" />
          </template>
        </DbMenuItem>
      </DbSubmenu>
      <div
        v-if="Object.keys(toolboxFavorMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'redis.toolbox'"
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <FunController
        controller-id="toolbox"
        module-id="redis">
        <DbMenuItem
          v-db-console="'redis.toolbox'"
          icon="tools"
          route-name="RedisToolbox">
          {{ t('工具箱') }}
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { menuGroupList, toolboxMenuList } from '@views/db-manage/redis/toolbox/toolboxMenuList';

  import DbMenuItem from '../../../menu/Item.vue';
  import DbSubmenu from '../../../menu/Submenu.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';
  import { useToolboxFavor } from './hooks/useToolboxFavor';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.REDIS, toolboxMenuList, menuGroupList);
</script>
