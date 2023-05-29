<template>
  <BkSubmenu
    v-if="isShow && currentMenu"
    :key="currentMenu.id"
    :title="currentMenu.name">
    <template #icon>
      <i :class="currentMenu.icon" />
    </template>
    <template
      v-for="childMenu in currentMenu.children"
      :key="childMenu.id">
      <BkMenuItem
        v-if="favorMap[childMenu.id]"
        :key="childMenu.id">
        <span
          v-overflow-tips.right
          class="text-overflow">
          {{ childMenu.name }}
        </span>
      </BkMenuItem>
    </template>
  </BkSubmenu>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref, watch } from 'vue';

  import mysqlToolboxMenuConfig from '@views/mysql/toolbox-menu';

  interface Props {
    id: string;
    favorMap: Record<string, boolean>;
    toolboxMenuConfig: typeof mysqlToolboxMenuConfig;
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
