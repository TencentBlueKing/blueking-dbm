<template>
  <FunController module-id="oracle">
    <MenuGroup
      :db-type="DBTypes.ORACLE"
      :is-error="isError">
      <FunController
        controller-id="oracle_primary_standby"
        module-id="oracle">
        <BkSubmenu key="OracleManage">
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <template #title>
            <span>{{ t('主从') }}</span>
            <CountTag
              :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
              role="cluster" />
          </template>
          <BkMenuItem key="OracleHaClusterList">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('集群视图') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
              role="cluster" />
          </BkMenuItem>
          <BkMenuItem
            key="OracleHaInstanceList"
            v-db-console="'oracle.haInstanceList'">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('实例视图') }}
            </span>
            <CountTag
              :cluster-type="ClusterTypes.ORACLE_PRIMARY_STANDBY"
              role="instance" />
          </BkMenuItem>
        </BkSubmenu>
      </FunController>
      <FunController
        controller-id="oracle_single_none"
        module-id="oracle">
        <BkMenuItem key="OracleSingleClusterList">
          <template #icon>
            <DbIcon type="node" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('单节点') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.ORACLE_SINGLE_NONE"
            role="cluster" />
        </BkMenuItem>
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
        <BkMenuItem
          key="OracleToolbox"
          v-db-console="'oracle.toolbox'">
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

  import { toolboxMenuList } from '@views/db-manage/oracle/toolbox/Index.vue';

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
