<template>
  <RouterView />
  <DbaHelper :biz-id="bizId" />
</template>
<script setup lang="ts">
  import DbaHelper from '@views/db-manage/common/DbaHelper.vue';

  const bizId = window.PROJECT_CONFIG.BIZ_ID;
</script>
