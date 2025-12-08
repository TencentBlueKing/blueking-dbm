<template>
  <FunController
    controller-id="tendbcluster"
    module-id="mysql">
    <MenuGroup
      :db-type="DBTypes.TENDBCLUSTER"
      :is-error="isError">
      <BkSubmenu key="tendb-cluster-manage">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <template #title>
          <span>{{ t('TendbCluster集群') }}</span>
          <CountTag
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            role="cluster" />
        </template>
        <BkMenuItem key="SpiderManage">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            role="cluster" />
        </BkMenuItem>
        <BkMenuItem
          key="tendbClusterInstance"
          v-db-console="'tendbCluster.instanceManage'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
          <CountTag
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            role="instance" />
        </BkMenuItem>
      </BkSubmenu>
      <BkMenuItem
        key="spiderPartitionManage"
        v-db-console="'tendbCluster.partitionManage'">
        <template #icon>
          <DbIcon type="mobanshili" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('分区管理') }}
        </span>
      </BkMenuItem>
      <BkSubmenu
        key="spider-permission"
        v-db-console="'tendbCluster.permissionManage'"
        :title="t('权限管理')">
        <template #icon>
          <DbIcon type="history" />
        </template>
        <BkMenuItem key="spiderPermission">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权规则') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="SpiderPermissionRetrieve">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('权限查询') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="spiderWhitelist">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权白名单') }}
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
        v-db-console="'tendbCluster.toolbox'"
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <BkMenuItem
        key="spiderToolbox"
        v-db-console="'tendbCluster.toolbox'">
        <template #icon>
          <DbIcon type="tools" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('工具箱') }}
        </span>
      </BkMenuItem>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/tendb-cluster/toolbox/Index.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';
  import { useToolboxFavor } from './hooks/useToolboxFavor';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.TENDBCLUSTER, toolboxMenuList);
</script>
