<template>
  <FunController module-id="sqlserver">
    <MenuGroup
      :db-type="DBTypes.SQLSERVER"
      :is-error="isError">
      <BkSubmenu key="SqlServerHaClusterManage">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <template #title>
          <span>{{ t('主从') }}</span>
          <CountTag
            :cluster-type="ClusterTypes.SQLSERVER_HA"
            role="cluster" />
        </template>
        <BkMenuItem key="SqlServerHaCluster">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.SQLSERVER_HA"
            role="cluster" />
        </BkMenuItem>
        <BkMenuItem
          key="SqlServerHaInstanceList"
          v-db-console="'sqlserver.haInstanceList'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.SQLSERVER_HA"
            role="instance" />
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
        <CountTag
          :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
          role="cluster" />
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
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/sqlserver/toolbox/Index.vue';

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
