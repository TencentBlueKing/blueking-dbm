<template>
  <FunController module-id="mongodb">
    <MenuGroup
      :db-type="DBTypes.MONGODB"
      :is-error="isError">
      <FunController
        controller-id="replicaSetList"
        module-id="mongodb">
        <DbSubmenu
          icon="cluster"
          :title="t('副本集群')">
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
              role="cluster" />
          </template>
          <DbMenuItem route-name="MongoDBReplicaSet">
            {{ t('集群管理') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
                role="cluster" />
            </template>
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'mongodb.replicaSetInstanceManage'"
            route-name="mongodbReplicaSetInstanceList">
            {{ t('实例视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
                role="instance" />
            </template>
          </DbMenuItem>
        </DbSubmenu>
      </FunController>
      <FunController
        controller-id="sharedClusterList"
        module-id="mongodb">
        <DbSubmenu
          icon="history"
          :title="t('分片集群')">
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
              role="cluster" />
          </template>
          <DbMenuItem route-name="MongoDBSharedCluster">
            {{ t('集群管理') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
                role="cluster" />
            </template>
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'mongodb.sharedClusterInstanceManage'"
            route-name="mongodbShareClusterInstanceList">
            {{ t('实例视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
                role="instance" />
            </template>
          </DbMenuItem>
        </DbSubmenu>
      </FunController>
      <DbSubmenu
        id="mongodb-permission"
        v-db-console="'mongodb.permissionManage'"
        icon="history"
        :title="t('权限管理')">
        <DbMenuItem route-name="MongodbPermission">
          {{ t('授权规则') }}
        </DbMenuItem>
      </DbSubmenu>
      <div
        v-if="Object.keys(toolboxFavorMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'mongodb.toolbox'"
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <FunController
        controller-id="toolbox"
        module-id="mongodb">
        <DbMenuItem
          v-db-console="'mongodb.toolbox'"
          icon="tools"
          route-name="MongoToolbox">
          {{ t('工具箱') }}
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/mongodb/toolbox/toolboxMenuList';

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

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.MONGODB, toolboxMenuList);
</script>
