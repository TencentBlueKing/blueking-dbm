<template>
  <FunController module-id="mongodb">
    <MenuGroup
      :db-type="DBTypes.MONGODB"
      :is-error="isError">
      <FunController
        controller-id="replicaSetList"
        module-id="mongodb">
        <BkSubmenu>
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <template #title>
            <span>{{ t('副本集群') }}</span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
              role="cluster" />
          </template>
          <BkMenuItem key="MongoDBReplicaSet">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('集群管理') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
              role="cluster" />
          </BkMenuItem>
          <BkMenuItem
            key="mongodbReplicaSetInstanceList"
            v-db-console="'mongodb.replicaSetInstanceManage'">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('实例视图') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_REPLICA_SET"
              role="instance" />
          </BkMenuItem>
        </BkSubmenu>
      </FunController>
      <FunController
        controller-id="sharedClusterList"
        module-id="mongodb">
        <BkSubmenu>
          <template #icon>
            <DbIcon type="history" />
          </template>
          <template #title>
            <span>{{ t('分片集群') }}</span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
              role="cluster" />
          </template>
          <BkMenuItem key="MongoDBSharedCluster">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('集群管理') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
              role="cluster" />
          </BkMenuItem>
          <BkMenuItem
            key="mongodbShareClusterInstanceList"
            v-db-console="'mongodb.sharedClusterInstanceManage'">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('实例视图') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
              role="instance" />
          </BkMenuItem>
        </BkSubmenu>
      </FunController>
      <BkSubmenu
        key="mongodb-permission"
        v-db-console="'mongodb.permissionManage'"
        :title="t('权限管理')">
        <template #icon>
          <DbIcon type="history" />
        </template>
        <BkMenuItem key="MongodbPermission">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权规则') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
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
        <BkMenuItem
          key="MongoToolbox"
          v-db-console="'mongodb.toolbox'">
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

  import { toolboxMenuList } from '@views/db-manage/mongodb/toolbox/Index.vue';

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
