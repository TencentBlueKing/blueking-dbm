<template>
  <FunController
    controller-id="tendbcluster"
    module-id="mysql">
    <MenuGroup
      :db-type="DBTypes.TENDBCLUSTER"
      :is-error="isError">
      <DbSubmenu
        id="tendb-cluster-manage"
        icon="cluster"
        :title="t('TendbCluster集群')">
        <template #append>
          <CountTag
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            role="cluster" />
        </template>
        <DbMenuItem route-name="SpiderManage">
          {{ t('集群视图') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.TENDBCLUSTER"
              role="cluster" />
          </template>
        </DbMenuItem>
        <DbMenuItem
          v-db-console="'tendbCluster.instanceManage'"
          route-name="tendbClusterInstance">
          {{ t('实例视图') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.TENDBCLUSTER"
              role="instance" />
          </template>
        </DbMenuItem>
      </DbSubmenu>
      <DbMenuItem
        v-db-console="'tendbCluster.partitionManage'"
        icon="mobanshili"
        route-name="spiderPartitionManage">
        {{ t('分区管理') }}
      </DbMenuItem>
      <DbSubmenu
        id="spider-permission"
        v-db-console="'tendbCluster.permissionManage'"
        icon="history"
        :title="t('权限管理')">
        <DbMenuItem route-name="spiderPermission">
          {{ t('授权规则') }}
        </DbMenuItem>
        <DbMenuItem route-name="SpiderPermissionRetrieve">
          {{ t('权限查询') }}
        </DbMenuItem>
        <DbMenuItem route-name="spiderWhitelist">
          {{ t('授权白名单') }}
        </DbMenuItem>
      </DbSubmenu>
      <DbMenuItem
        v-db-console="'tendbCluster.toolbox'"
        icon="tools"
        route-name="TendbclusterToolbox">
        {{ t('工具箱') }}
      </DbMenuItem>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import DbMenuItem from '../../../menu/Item.vue';
  import DbSubmenu from '../../../menu/Submenu.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
