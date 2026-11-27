<template>
  <Menu
    v-if="isIndex"
    :menu-list="availableMenuList" />
  <Content
    v-else
    :menu-list="availableMenuList" />
</template>
<script setup lang="ts">
  import { filterControlledToolboxMenu } from '@views/db-manage/common/toolbox-new/common/utils';
  import Content from '@views/db-manage/common/toolbox-new/content/Index.vue';
  import Menu from '@views/db-manage/common/toolbox-new/menu/Index.vue';

  import { toolboxMenuList } from './toolboxMenuList';

  const route = useRoute();
  const availableMenuList = computed(() => filterControlledToolboxMenu(toolboxMenuList));

  const isIndex = computed(() => route.name === 'RedisToolboxIndex');
</script>
