<template>
  <FunController module-id="mysql">
    <MenuGroup
      :db-type="DBTypes.MYSQL"
      :is-error="isError">
      <FunController
        controller-id="tendbha"
        module-id="mysql">
        <DbSubmenu
          id="MysqlManage"
          icon="cluster"
          :title="t('主从')">
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.TENDBHA"
              role="cluster" />
          </template>
          <DbMenuItem route-name="tendbha">
            {{ t('集群视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.TENDBHA"
                role="cluster" />
            </template>
          </DbMenuItem>
          <DbMenuItem
            v-db-console="'mysql.haInstanceList'"
            route-name="DatabaseTendbhaInstance">
            {{ t('实例视图') }}
            <template #append>
              <CountTag
                :cluster-type="ClusterTypes.TENDBHA"
                role="instance" />
            </template>
          </DbMenuItem>
        </DbSubmenu>
      </FunController>
      <FunController
        controller-id="tendbsingle"
        module-id="mysql">
        <DbMenuItem
          v-db-console="'mysql.singleClusterList'"
          icon="node"
          route-name="tendbsingle">
          {{ t('单节点') }}
          <template #append>
            <CountTag
              :cluster-type="ClusterTypes.TENDBSINGLE"
              role="cluster" />
          </template>
        </DbMenuItem>
      </FunController>
      <DbMenuItem
        v-db-console="'mysql.partitionManage'"
        icon="mobanshili"
        route-name="mysqlPartitionManage">
        {{ t('分区管理') }}
      </DbMenuItem>
      <DbSubmenu
        id="database-permission"
        v-db-console="'mysql.permissionManage'"
        icon="history"
        :title="t('权限管理')">
        <DbMenuItem route-name="PermissionRules">
          {{ t('授权规则') }}
        </DbMenuItem>
        <DbMenuItem route-name="MysqlPermissionRetrieve">
          {{ t('权限查询') }}
        </DbMenuItem>
        <DbMenuItem route-name="mysqlWhitelist">
          {{ t('授权白名单') }}
        </DbMenuItem>
      </DbSubmenu>
      <FunController
        :controller-id="dumperControlId"
        module-id="mysql">
        <DbMenuItem
          v-db-console="'mysql.dataSubscription'"
          icon="mobanshili"
          route-name="DumperDataSubscription">
          {{ t('数据订阅') }}
        </DbMenuItem>
      </FunController>
      <FunController
        controller-id="toolbox"
        module-id="mysql">
        <DbMenuItem
          v-db-console="'mysql.toolbox'"
          icon="tools"
          route-name="MysqlToolbox">
          {{ t('工具箱') }}
        </DbMenuItem>
      </FunController>
    </MenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { FunctionKeys } from '@services/model/function-controller/functionController';

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

  const dumperControlId = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as FunctionKeys;
</script>
