<template>
  <FunController module-id="mongodb">
    <BkMenuGroup name="MongoDB">
      <BkSubmenu :title="t('集群管理')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="MongoDBReplicaSetList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('副本集集群') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="MongoDBSharedClusterList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('分片集群') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="mongodbInstance">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
      <BkSubmenu
        key="mongodb-permission"
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
    </BkMenuGroup>
    <ToolboxMenu
      v-for="toolboxGroupId in toolboxMenuSortList"
      :id="toolboxGroupId"
      :key="toolboxGroupId"
      :favor-map="favorMeunMap"
      :toolbox-menu-config="toolboxMenuConfig" />
    <FunController
      controller-id="toolbox"
      module-id="mongodb">
      <BkMenuItem key="MongoToolbox">
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
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/mongodb-manage/toolbox-menu';

  import { makeMap } from '@utils';

  import ToolboxMenu from './components/ToolboxMenu.vue';

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
