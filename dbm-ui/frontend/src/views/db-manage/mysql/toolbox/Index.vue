<template>
  <Menu
    v-if="isIndex"
    :menu-list="toolboxMenuList" />
  <Content
    v-else
    :menu-list="toolboxMenuList" />
</template>

<script setup lang="ts">
  import Content from '@views/db-manage/common/toolbox-new/content/Index.vue';
  import Menu from '@views/db-manage/common/toolbox-new/menu/Index.vue';

  import { toolboxMenuList } from './toolboxMenuList.ts';

  const route = useRoute();

  const isIndex = computed(() => route.name === 'MysqlToolboxIndex');
</script>
