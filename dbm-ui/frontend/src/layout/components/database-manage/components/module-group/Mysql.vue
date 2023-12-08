<template>
  <FunController module-id="mysql">
    <BkMenuGroup name="MySQL">
      <FunController
        controller-id="tendbsingle"
        module-id="mysql">
        <BkMenuItem key="DatabaseTendbsingle">
          <template #icon>
            <DbIcon type="node" />
          </template>
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('单节点') }}
          </span>
        </BkMenuItem>
      </FunController>
      <FunController
        controller-id="tendbha"
        module-id="mysql">
        <BkSubmenu
          key="MysqlManage"
          :title="t('主从')">
          <template #icon>
            <DbIcon type="cluster" />
          </template>
          <BkMenuItem key="DatabaseTendbha">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('集群视图') }}
            </span>
          </BkMenuItem>
          <BkMenuItem key="DatabaseTendbhaInstance">
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ t('实例视图') }}
            </span>
          </BkMenuItem>
        </BkSubmenu>
      </FunController>
      <BkMenuItem key="mysqlPartitionManage">
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
          key="DumperDataSubscription">
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
        v-if="Object.keys(favorMeunMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        :favor-map="favorMeunMap"
        :toolbox-menu-config="toolboxMenuConfig" />
      <FunController
        controller-id="toolbox"
        module-id="mysql">
        <BkMenuItem key="MySQLToolbox">
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
  import {
    onBeforeUnmount,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { FunctionKeys } from '@services/model/function-controller/functionController';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/mysql/toolbox-menu';

  import { makeMap } from '@utils';

  import ToolboxMenu from './components/ToolboxMenu.vue';

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const dumperControlId = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as FunctionKeys;

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value = userProfile.profile[UserPersonalSettings.MYSQL_TOOLBOX_MENUS]
      || toolboxMenuConfig.map(item => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.MYSQL_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();


  eventBus.on('MYSQL_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('MYSQL_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>

