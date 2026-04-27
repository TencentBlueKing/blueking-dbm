<template>
  <ToolBox
    :menu-group-list="menuGroupList"
    :menu-list="toolboxMenuList" />
</template>
<script setup lang="ts">
  import ToolBox from '@views/db-manage/common/toolbox/Index.vue';

  import { menuGroupList, toolboxMenuList } from './toolboxMenuList';
</script>
