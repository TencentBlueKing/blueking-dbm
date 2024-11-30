<template>
  <FunController module-id="sqlserver">
    <BkMenuGroup name="SqlServer">
      <BkSubmenu
        key="SqlServerHaClusterManage"
        :title="t('主从')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="SqlServerHaClusterList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
        </BkMenuItem>
        <BkMenuItem
          key="SqlServerHaInstanceList"
          v-db-console="'sqlserver.haInstanceList'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
      <BkMenuItem
        key="SqlServerSingle"
        v-db-console="'sqlserver.singleClusterList'">
        <template #icon>
          <DbIcon type="node" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('单节点') }}
        </span>
      </BkMenuItem>
      <BkSubmenu
        key="sqlserver-permission"
        v-db-console="'sqlserver.permissionManage'"
        :title="t('权限管理')">
        <template #icon>
          <DbIcon type="history" />
        </template>
        <BkMenuItem key="SqlServerPermissionRules">
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
        :favor-map="favorMeunMap"
        :toolbox-menu-config="toolboxMenuConfig" />
      <FunController
        controller-id="sqlserver_tool"
        module-id="sqlserver">
        <BkMenuItem key="sqlserverToolbox">
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
  import { onBeforeUnmount, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/db-manage/sqlserver/toolbox-menu';

  import { makeMap } from '@utils';

  import ToolboxMenu from './components/ToolboxMenu.vue';

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value =
      userProfile.profile[UserPersonalSettings.SQLSERVER_TOOLBOX_MENUS] || toolboxMenuConfig.map((item) => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.SQLSERVER_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('SQLSERVER_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('SQLSERVER_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
