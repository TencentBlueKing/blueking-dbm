<template>
  <DbSubmenu
    v-if="isShow && currentMenu"
    :id="currentMenu.id"
    :key="currentMenu.id"
    :title="currentMenu.name">
    <template #icon>
      <i :class="currentMenu.icon" />
    </template>
    <template
      v-for="childMenu in currentMenu.children"
      :key="childMenu.id">
      <DbMenuItem
        v-if="favorMap[childMenu.id]"
        :key="childMenu.id"
        :route-name="childMenu.id">
        {{ childMenu.name }}
      </DbMenuItem>
    </template>
  </DbSubmenu>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref, watch } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';

  import DbToolbox from '@views/db-manage/common/toolbox/Index.vue';

  import DbMenuItem from '../../../../menu/Item.vue';
  import DbSubmenu from '../../../../menu/Submenu.vue';

  interface Props {
    favorMap: Record<string, boolean>;
    id: string;
    toolboxMenuConfig: ComponentProps<typeof DbToolbox>['menuList'];
  }

  const props = defineProps<Props>();

  const currentMenu = _.find(props.toolboxMenuConfig, (item) => item.id === props.id);

  const isShow = ref(false);

  watch(
    () => props.favorMap,
    () => {
      if (!currentMenu) {
        return;
      }
      isShow.value = _.some(currentMenu.children, (item) => props.favorMap[item.id]);
    },
    {
      immediate: true,
    },
  );
</script>
