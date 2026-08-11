<template>
  <FunController module-id="oracle">
    <MenuGroup
      :db-type="DBTypes.ORACLE"
      :is-error="isError">
      <FunController
        controller-id="oracle_primary_standby"
        module-id="oracle">
        <DbSubmenu
          id="OracleManage"
          icon="cluster"
          :title="t('主从')">
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
              role="cluster" />
          </template>
          <DbMenuItem route-name="OracleHaClusterList">
            {{ t('集群视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
                role="cluster" />
            </template>
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'oracle.haInstanceList'"
            route-name="OracleHaInstanceList">
            {{ t('实例视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
                role="instance" />
            </template>
          </DbMenuItem>
        </DbSubmenu>
      </FunController>
      <FunController
        controller-id="oracle_single_none"
        module-id="oracle">
        <DbMenuItem
          icon="node"
          route-name="OracleSingleClusterList">
          {{ t('单节点') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE"
              role="cluster" />
          </template>
        </DbMenuItem>
      </FunController>
      <div
        v-if="Object.keys(toolboxFavorMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'oracle.toolbox'"
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <FunController
        controller-id="toolbox"
        module-id="oracle">
        <DbMenuItem
          v-db-console="'oracle.toolbox'"
          icon="tools"
          route-name="OracleToolbox">
          {{ t('工具箱') }}
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/oracle/toolbox/toolboxMenuList';

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

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.ORACLE, toolboxMenuList);
</script>
