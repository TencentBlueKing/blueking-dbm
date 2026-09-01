<template>
  <FunController module-id="sqlserver">
    <MenuGroup
      :db-type="DBTypes.SQLSERVER"
      :is-error="isError">
      <DbSubmenu
        id="SqlServerHaClusterManage"
        icon="cluster"
        :title="t('主从')">
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.SQLSERVER_HA"
            role="cluster" />
        </template>
        <DbMenuItem route-name="SqlServerHaCluster">
          {{ t('集群视图') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.SQLSERVER_HA"
              role="cluster" />
          </template>
        </DbMenuItem>
        <DbMenuItem
          v-db-console="'sqlserver.haInstanceList'"
          route-name="SqlServerHaInstanceList">
          {{ t('实例视图') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.SQLSERVER_HA"
              role="instance" />
          </template>
        </DbMenuItem>
      </DbSubmenu>
      <DbMenuItem
        v-db-console="'sqlserver.singleClusterList'"
        icon="node"
        route-name="SqlServerSingle">
        {{ t('单节点') }}
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
            role="cluster" />
        </template>
      </DbMenuItem>
      <DbSubmenu
        id="sqlserver-permission"
        v-db-console="'sqlserver.permissionManage'"
        icon="history"
        :title="t('权限管理')">
        <DbMenuItem route-name="SqlServerPermissionRules">
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
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <FunController
        controller-id="sqlserver_tool"
        module-id="sqlserver">
        <DbMenuItem
          icon="tools"
          route-name="sqlserverToolbox">
          {{ t('工具箱') }}
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/sqlserver/toolbox/toolboxMenuList';

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

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.SQLSERVER, toolboxMenuList);
</script>
