<template>
  <FunController module-id="mysql">
    <MenuGroup
      :db-type="DBTypes.MYSQL"
      :is-error="isError">
      <FunController
        controller-id="tendbha"
        module-id="mysql">
        <BkSubmenu key="MysqlManage">
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <template #title>
            <span>{{ t('主从') }}</span>
            <CountTag
              :cluster-type="ClusterTypes.TENDBHA"
              role="cluster" />
          </template>
          <BkMenuItem key="tendbha">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('集群视图') }}
              <CountTag
                :cluster-type="ClusterTypes.TENDBHA"
                role="cluster" />
            </span>
          </BkMenuItem>
          <BkMenuItem
            key="DatabaseTendbhaInstance"
            v-db-console="'mysql.haInstanceList'">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('实例视图') }}
              <CountTag
                :cluster-type="ClusterTypes.TENDBHA"
                role="instance" />
            </span>
          </BkMenuItem>
        </BkSubmenu>
      </FunController>
      <FunController
        controller-id="tendbsingle"
        module-id="mysql">
        <BkMenuItem
          key="tendbsingle"
          v-db-console="'mysql.singleClusterList'">
          <template #icon>
            <DbIcon type="node" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('单节点') }}
            <CountTag
              :cluster-type="ClusterTypes.TENDBSINGLE"
              role="cluster" />
          </span>
        </BkMenuItem>
      </FunController>
      <BkMenuItem
        key="mysqlPartitionManage"
        v-db-console="'mysql.partitionManage'">
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
        key="database-permission"
        v-db-console="'mysql.permissionManage'"
        :title="t('权限管理')">
        <template #icon>
          <DbIcon type="history" />
        </template>
        <BkMenuItem key="PermissionRules">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权规则') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="MysqlPermissionRetrieve">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('权限查询') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="mysqlWhitelist">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权白名单') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
      <FunController
        :controller-id="dumperControlId"
        module-id="mysql">
        <BkMenuItem
          key="DumperDataSubscription"
          v-db-console="'mysql.dataSubscription'">
          <template #icon>
            <i class="db-icon-mobanshili" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('数据订阅') }}
          </span>
        </BkMenuItem>
      </FunController>
      <div
        v-if="Object.keys(toolboxFavorMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'mysql.toolbox'"
        :favor-map="toolboxFavorMap"
        :toolbox-menu-config="toolboxMenuList" />
      <FunController
        controller-id="toolbox"
        module-id="mysql">
        <BkMenuItem
          key="MySQLToolbox"
          v-db-console="'mysql.toolbox'">
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

  import type { FunctionKeys } from '@services/model/function-controller/functionController';

  import { ClusterTypes, DBTypes } from '@common/const';

  import { toolboxMenuList } from '@views/db-manage/mysql/toolbox/IndexNew.vue';

  import CountTag from './components/CountTag.vue';
  import MenuGroup from './components/MenuGroup.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';
  import { useToolboxFavor } from './hooks/useToolboxFavor';

  interface Props {
    isError: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const dumperControlId = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as FunctionKeys;

  const { toolboxFavorMap, toolboxMenuSortList } = useToolboxFavor(DBTypes.MYSQL, toolboxMenuList);
</script>
