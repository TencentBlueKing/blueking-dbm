<template>
  <ToolBox :menu-list="toolboxMenuList" />
</template>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';

  import { toolboxMenuList } from './toolboxMenuList';
</script>
