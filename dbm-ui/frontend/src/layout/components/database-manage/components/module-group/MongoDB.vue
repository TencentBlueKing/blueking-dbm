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
              role="cluster" />
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
              role="cluster" />
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
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'mongodb.toolbox'"
        :favor-map="favorMeunMap"
        :toolbox-menu-config="toolboxMenuConfig" />
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

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/db-manage/mongodb/toolbox-menu';

  import { makeMap } from '@utils';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value =
      userProfile.profile[UserPersonalSettings.MONGO_TOOLBOX_MENUS] || toolboxMenuConfig.map((item) => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.MONGO_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('MONGO_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('MONGO_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
