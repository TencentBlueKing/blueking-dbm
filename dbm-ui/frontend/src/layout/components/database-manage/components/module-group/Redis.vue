<template>
  <FunController module-id="redis">
    <MenuGroup
      :db-type="DBTypes.REDIS"
      :is-error="isError">
      <BkSubmenu key="RedisManage">
        <template #icon>
          <DbIcon type="fenbushijiqun" />
        </template>
        <template #title>
          <span>{{ t('集群') }}</span>
          <!-- prettier-ignore -->
          <CountTag :cluster-type="('redis_cluster' as ClusterTypes)" role="cluster" />
        </template>
        <BkMenuItem key="redisCluster">
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
        <BkMenuItem key="DatabaseRedisHa">
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
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { menuGroupList, toolboxMenuList } from '@views/db-manage/redis/toolbox/Index.vue';

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
