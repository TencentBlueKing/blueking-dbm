<template>
  <FunController
    controller-id="tendbcluster"
    module-id="mysql">
    <BkMenuGroup name="Tendb Cluster">
      <BkSubmenu
        key="tendb-cluster-manage"
        :title="t('TendbCluster集群')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="SpiderManage">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('集群视图') }}
          </span>
        </BkMenuItem>
        <BkMenuItem
          key="tendbClusterInstance"
          v-db-console="'tendbCluster.instanceManage'">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
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
        v-if="Object.keys(favorMeunMap).length > 0"
        class="split-line" />
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'tendbCluster.toolbox'"
        :favor-map="favorMeunMap"
        :toolbox-menu-config="toolboxMenuConfig" />
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
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/db-manage/tendb-cluster/toolbox-menu';

  import { makeMap } from '@utils';

  import ToolboxMenu from './components/ToolboxMenu.vue';

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value =
      userProfile.profile[UserPersonalSettings.SPIDER_TOOLBOX_MENUS] || toolboxMenuConfig.map((item) => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.SPIDER_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('SPIDER_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('SPIDER_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
