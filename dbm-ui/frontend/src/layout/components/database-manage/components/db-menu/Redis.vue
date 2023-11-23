<template>
  <FunController module-id="redis">
    <BkMenuGroup name="Redis">
      <BkMenuItem key="RedisManage">
        <template #icon>
          <DbIcon type="redis" />
        </template>
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ t('集群管理') }}
        </span>
      </BkMenuItem>
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
        module-id="redis">
        <BkMenuItem key="RedisToolbox">
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

  import { useEventBus } from '@hooks';

  import { useUserProfile  } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import toolboxMenuConfig from '@views/redis/toolbox-menu';

  import { makeMap } from '@utils';

  import ToolboxMenu from './components/ToolboxMenu.vue';

  console.log('toolboxMenuConfig = ', toolboxMenuConfig);

  const userProfile = useUserProfile();
  const { t } = useI18n();
  const eventBus = useEventBus();

  const toolboxMenuSortList = shallowRef<string[]>([]);
  const favorMeunMap = shallowRef<Record<string, boolean>>({});

  const renderToolboxMenu = () => {
    toolboxMenuSortList.value = userProfile.profile[UserPersonalSettings.REDIS_TOOLBOX_MENUS]
      || toolboxMenuConfig.map(item => item.id);
    favorMeunMap.value = makeMap(userProfile.profile[UserPersonalSettings.REDIS_TOOLBOX_FAVOR]);
  };

  renderToolboxMenu();

  eventBus.on('REDIS_TOOLBOX_CHANGE', renderToolboxMenu);

  onBeforeUnmount(() => {
    eventBus.off('REDIS_TOOLBOX_CHANGE', renderToolboxMenu);
  });
</script>
