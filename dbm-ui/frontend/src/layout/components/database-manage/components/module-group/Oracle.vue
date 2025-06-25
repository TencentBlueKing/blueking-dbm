<template>
  <FunController module-id="oracle">
    <BkMenuGroup name="Oracle">
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
      <ToolboxMenu
        v-for="toolboxGroupId in toolboxMenuSortList"
        :id="toolboxGroupId"
        :key="toolboxGroupId"
        v-db-console="'oracle.toolbox'"
        :favor-map="favorMeunMap"
        :toolbox-menu-config="toolboxMenuConfig" />
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
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/db-manage/oracle/toolbox-menu';

  import { makeMap } from '@utils';

  import CountTag from './components/CountTag.vue';
  import ToolboxMenu from './components/ToolboxMenu.vue';

  const userProfile = useUserProfile();
  const eventBus = useEventBus();
  const { t } = useI18n();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value =
      userProfile.profile[UserPersonalSettings.ORACLE_TOOLBOX_MENUS] || toolboxMenuConfig.map((item) => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.ORACLE_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('ORACLE_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('ORACLE_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
